import os
import sys

os.environ['PYTHONUNBUFFERED'] = '1'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

import wave
import time
import math
import array
import json
import queue
import signal
import threading
import logging
import subprocess
from typing import Optional

import sounddevice as sd
import numpy as np
import requests
from websockets.sync.client import connect
from vosk import Model, KaldiRecognizer
import webrtcvad

RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
BLOCKSIZE = 1600  # 100ms a 16kHz – mais estável, menos callbacks por segundo
WAVE_OUTPUT = "request.wav"
WAVE_RESPONSE = "response.wav"
SERVER_URL = "http://pvserver:10001"
DEVICE_ID = "server-satellite-sala"
ROOM_ID = "ROOM_LIVING"

wake_word = "alfredo"
wake_variants = [
    "alfredo", "alfre", "fredo", "frente", "al fredo",
    "alfredou", "alfreu", "alfrente", "alfred"
]

alarm_process = None
audio_stream: Optional[sd.InputStream] = None
vosk_model: Optional[Model] = None
vosk_rec: Optional[KaldiRecognizer] = None
vad: Optional[webrtcvad.Vad] = None

# Variáveis Globais de Estado
is_recording = False
has_spoken = False
silence_frames = 0
recording_buffer = bytearray()
full_audio_buffer = bytearray()
dashcam_buffer = bytearray()
is_streaming = False
stream_queue: queue.Queue = queue.Queue()
ws_instance = None

# Pre-amp de software controlável
SOFTWARE_MULTIPLIER = 1.0

# Variáveis de calibração do Noise Gate
is_calibrated = False
calibration_frames = 0
calibration_sum = 0
noise_threshold = 2000
full_audio_buffer = bytearray()

# Noise Gate com Hold Time (evita cortar sílabas fracas de voz distante)
noise_gate_hold = 0
NOISE_GATE_HOLD_FRAMES = 10  # 10 chunks de 20ms = 200ms de hold antes de fechar o gate

# Modo Dashcam
DASHCAM_SECONDS = 3
DASHCAM_MAX_BYTES = DASHCAM_SECONDS * RATE * 2 # 16kHz, 16-bit (2 bytes por sample)
dashcam_buffer = bytearray()

# Coeficiente do filtro IIR low-pass (estado persistente entre callbacks)
_iir_prev_sample = 0.0


def get_rms(data: bytes) -> float:
    samples = array.array('h', data[:len(data) - (len(data) % 2)])
    if not samples:
        return 0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def clean_audio(samples: np.ndarray) -> np.ndarray:
    """Pipeline de limpeza de áudio USB em 3 etapas.
    
    1. Remove DC offset (bias de microfones USB baratos)
    2. Interpola pops/spikes USB (mudanças bruscas > 8000 em 1 sample)
    3. Filtro IIR low-pass de 1ª ordem (cutoff ~7kHz a 16kHz sample rate)
    """
    global _iir_prev_sample
    audio = samples.astype(np.float32)

    # Etapa 1: Remove DC offset
    audio -= np.mean(audio)

    # Etapa 2: Spike removal (interpola pops USB)
    diff = np.abs(np.diff(audio, prepend=audio[0]))
    spike_mask = diff > 8000  # Mudanças bruscas > 8000 são pops
    if np.any(spike_mask):
        indices = np.where(spike_mask)[0]
        for idx in indices:
            left = max(0, idx - 1)
            right = min(len(audio) - 1, idx + 1)
            audio[idx] = (audio[left] + audio[right]) / 2

    # Etapa 3: Low-pass IIR de 1ª ordem (alpha=0.72 ≈ cutoff 7kHz para 16kHz SR)
    # Preserva estado entre callbacks para evitar descontinuidades
    alpha = 0.72
    audio[0] = alpha * audio[0] + (1 - alpha) * _iir_prev_sample
    for i in range(1, len(audio)):
        audio[i] = alpha * audio[i] + (1 - alpha) * audio[i - 1]
    _iir_prev_sample = float(audio[-1])

    return audio


def soft_clip(audio: np.ndarray, threshold: float = 28000) -> np.ndarray:
    """Comprime suavemente picos ao invés de cortar abruptamente (hard clip).
    
    Usa tanh para comprimir gradualmente valores acima do threshold,
    evitando os estouros audíveis que np.clip() causa.
    """
    mask = np.abs(audio) > threshold
    if np.any(mask):
        sign = np.sign(audio[mask])
        excess = np.abs(audio[mask]) - threshold
        max_excess = 32767 - threshold  # 4767
        compressed = threshold + max_excess * np.tanh(excess / max_excess)
        audio[mask] = sign * compressed
    return audio


def play_alarm_loop():
    global alarm_process
    alarm_file = os.path.join(os.path.dirname(__file__), "alarm.wav")
    if not os.path.exists(alarm_file):
        print("⚠️ Arquivo de alarme não encontrado.")
        return
    stop_alarm()
    print("🔔 Despertador tocando!")
    cmd = f"while true; do aplay -q '{alarm_file}'; done"
    alarm_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)


def stop_alarm():
    global alarm_process
    if alarm_process:
        try:
            os.killpg(os.getpgid(alarm_process.pid), signal.SIGTERM)
        except Exception:
            pass
        alarm_process = None


def register_device():
    print(f"Registrando dispositivo {DEVICE_ID} no servidor...")
    url = f"{SERVER_URL}/api/devices/register"
    payload = {
        "device_id": DEVICE_ID,
        "room_id": ROOM_ID,
        "hardware": "linux-server-satellite",
        "firmware_version": "1.0.0",
        "capabilities": ["microphone", "speaker"]
    }
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            print(f"Registro OK! Servidor respondeu: {response.json()['message']}")
            try:
                settings_res = requests.get(f"{SERVER_URL}/api/dashboard/settings", timeout=3)
                if settings_res.status_code == 200:
                    settings_data = settings_res.json()
                    if "assistant_name" in settings_data:
                        global wake_word
                        wake_word = settings_data["assistant_name"].lower()
                        print(f"📡 Wake Word sincronizado com o servidor: {wake_word.upper()}")
            except Exception as e:
                print(f"Aviso: Não foi possível sincronizar o Wake Word: {e}")
            return True
        except Exception as e:
            print(f"Falha ao registrar (tentativa {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return False


def play_audio(filename):
    print("🔊 Reproduzindo resposta (volume amplificado)...", flush=True)
    try:
        amplified = "response_loud.wav"
        subprocess.run(
            ['sox', filename, amplified, 'vol', '3.0'],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.run(['aplay', '-q', amplified], check=True)
    except Exception as e:
        print(f"Erro ao reproduzir áudio: {e}. Tentando sem amplificação...", flush=True)
        try:
            subprocess.run(['aplay', '-q', filename], check=True)
        except Exception as e2:
            print(f"Erro fatal ao reproduzir: {e2}", flush=True)


def send_audio_and_play(filename):
    print("Enviando áudio para o servidor (Groq API STT e Router)...")
    url = f"{SERVER_URL}/api/voice"
    headers = {
        "X-Device-ID": DEVICE_ID,
        "X-Room-ID": ROOM_ID,
        "Authorization": "Bearer mock-token-123"
    }
    try:
        with open(filename, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            start_time = time.time()
            response = requests.post(url, headers=headers, files=files, stream=True)
            
        if response.status_code == 200:
            first_byte_received = False
            
            player_process = subprocess.Popen(
                ['ffplay', '-nodisp', '-autoexit', '-i', 'pipe:0'],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    if not first_byte_received:
                        ttfb = time.time() - start_time
                        print(f"🔊 Áudio iniciado em {ttfb:.2f} segundos!", flush=True)
                        first_byte_received = True
                    player_process.stdin.write(chunk)
                    player_process.stdin.flush()
                    
            player_process.stdin.close()
            player_process.wait()
            
            total_time = time.time() - start_time
            print(f"✅ Interação concluída. Tempo total: {total_time:.2f} segundos.", flush=True)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Falha na comunicação com o servidor: {e}")


def audio_callback(indata: np.ndarray, frames: int, time_info, status: sd.CallbackFlags):
    global vosk_rec, is_recording, has_spoken, silence_frames, recording_buffer
    global is_calibrated, calibration_frames, calibration_sum, noise_threshold
    global full_audio_buffer, dashcam_buffer, SOFTWARE_MULTIPLIER, noise_gate_hold

    # Tratar overflow ao invés de descartar silenciosamente
    if status:
        if status.input_overflow:
            print("⚠️ [AUDIO] Buffer overflow detectado! Áudio pode picotar.", flush=True)
        # Continua processando ao invés de descartar o frame

    # Pipeline DSP robusto: DC removal → spike interpolation → low-pass IIR
    flattened = indata.flatten()
    cleaned = clean_audio(flattened)
    
    # Amplificador de software dinâmico
    if SOFTWARE_MULTIPLIER != 1.0:
        cleaned = cleaned * SOFTWARE_MULTIPLIER

    # Soft-clip: comprime gradualmente ao invés de cortar abruptamente
    cleaned = soft_clip(cleaned)
    cleaned = cleaned.astype(np.int16)
    bytes_data = cleaned.tobytes()

    # Calibração inicial (aprox. 2 segundos para ler o chiado do ambiente)
    if not is_calibrated:
        rms = get_rms(bytes_data)
        calibration_sum += rms
        calibration_frames += 1
        required_frames = int((RATE / BLOCKSIZE) * 2.0)
        
        if calibration_frames >= required_frames:
            avg_noise = calibration_sum / calibration_frames
            # Margem um pouco acima do chiado ambiente para não bloquear voz distante
            noise_threshold = avg_noise + 200
            print(f"\n🎙️ [CALIBRAÇÃO] Ruído de fundo médio: {avg_noise:.1f}")
            print(f"🎙️ [CALIBRAÇÃO] Noise Threshold dinâmico definido para: {noise_threshold:.1f}\n")
            is_calibrated = True
        return  # Não processa áudio durante os 2s de calibração

    if vosk_rec and not is_recording:
        # Dashcam: manter sempre os últimos 3 segundos na memória
        dashcam_buffer.extend(bytes_data)
        if len(dashcam_buffer) > DASHCAM_MAX_BYTES:
            del dashcam_buffer[:-DASHCAM_MAX_BYTES]

        if vosk_rec.AcceptWaveform(bytes_data):
            result = json.loads(vosk_rec.Result())
            text = result.get('text', '').lower()
            if text.strip() and any(v in text for v in wake_variants):
                print(f"🔔 Palavra de ativação '{wake_word.upper()}' detectada pelo Vosk!", flush=True)
                _start_recording()

    if is_streaming:
        stream_queue.put_nowait(bytes_data)

    if is_recording:
        recording_buffer.extend(bytes_data)
        full_audio_buffer.extend(bytes_data)
        offset = 0
        while offset + 320 <= len(recording_buffer):
            chunk = recording_buffer[offset:offset + 320]
            offset += 320
            is_speech = vad.is_speech(chunk, RATE)
            rms = get_rms(chunk)
            
            # Noise Gate com Hold Time: mantém o gate aberto por 200ms
            # após a última detecção de voz, evitando cortar sílabas fracas
            if rms < noise_threshold:
                if noise_gate_hold > 0:
                    noise_gate_hold -= 1
                    # Gate ainda aberto (hold) – respeita o VAD original
                else:
                    is_speech = False
            else:
                noise_gate_hold = NOISE_GATE_HOLD_FRAMES  # Reset hold timer
                
            if is_speech:
                has_spoken = True
                silence_frames = 0
            elif has_spoken:
                silence_frames += 1
                
        recording_buffer = bytearray(recording_buffer[offset:])

        total_frames = len(full_audio_buffer) // 320
        max_silence = int(1.5 * RATE / 160)
        timeout_frames = int(5 * RATE / 160)
        max_total = int(15 * RATE / 160)

        if has_spoken and silence_frames > max_silence:
            print("⏹️ Silêncio detectado. Fim da gravação.", flush=True)
            _finish_recording()
        elif not has_spoken and total_frames > timeout_frames:
            print("⏳ Ninguém falou nada (5s). Cancelando gravação.", flush=True)
            is_recording = False
            recording_buffer.clear()
        elif total_frames > max_total:
            print("⏳ Tempo máximo atingido.", flush=True)
            _finish_recording()


def _start_recording():
    global is_recording, recording_buffer, has_spoken, silence_frames, vosk_rec
    global full_audio_buffer, dashcam_buffer
    is_recording = True
    recording_buffer = bytearray()
    
    # Injetando o passado (Dashcam) no buffer final!
    full_audio_buffer = bytearray(dashcam_buffer)
    dashcam_buffer.clear()
    
    # Como o Vosk acabou de identificar a palavra de ativação, já sabemos que a pessoa falou.
    # Evita que o VAD descarte o áudio se a pessoa falou rápido demais e só sobrou silêncio vivo.
    has_spoken = True
    silence_frames = 0
    vosk_rec = KaldiRecognizer(vosk_model, RATE)
    stop_alarm()
    
    # Beep foi removido para interação mais natural e fluida
    print("🔴 [GRAVANDO COM DASHCAM] Ouvindo comando (incluindo o passado)...", flush=True)


def _finish_recording():
    global is_recording, full_audio_buffer
    is_recording = False
    buf = bytes(full_audio_buffer)
    recording_buffer.clear()
    full_audio_buffer.clear()

    if len(buf) < 3200:
        print("Áudio muito curto, ignorando.", flush=True)
        return

    print(f"⏹️ [VAD] Tamanho do áudio: {len(buf)} bytes. Enviando...", flush=True)
    threading.Thread(target=_send_and_play, args=(buf,), daemon=True).start()


def _send_and_play(audio_data: bytes):
    t_start = time.time()
    with wave.open(WAVE_OUTPUT, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(audio_data)

    url = f"{SERVER_URL}/api/voice"
    headers = {
        "X-Device-ID": DEVICE_ID,
        "X-Room-ID": ROOM_ID,
        "Authorization": "Bearer mock-token-123"
    }
    try:
        with open(WAVE_OUTPUT, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            t_send = time.time()
            response = requests.post(url, headers=headers, files=files, timeout=30)

        if response.status_code == 200:
            t_response = time.time()
            server_latency = t_response - t_send
            total_latency = t_response - t_start
            print(f"✅ [RESPOSTA] Servidor: {server_latency:.1f}s | Total: {total_latency:.1f}s", flush=True)
            with open(WAVE_RESPONSE, 'wb') as f:
                f.write(response.content)
            play_audio(WAVE_RESPONSE)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Falha na comunicação com o servidor: {e}")


def stream_worker():
    global ws_instance
    while True:
        try:
            data = stream_queue.get(timeout=1)
            if ws_instance and is_streaming:
                try:
                    ws_instance.send(data)
                except Exception:
                    pass
        except queue.Empty:
            continue


def websocket_loop():
    global ws_instance, is_streaming, wake_word
    ws_url = f"ws://{SERVER_URL.replace('http://', '').replace('https://', '')}/api/ws/satellite/{DEVICE_ID}"

    while True:
        try:
            print(f"Tentando conectar ao WebSocket em {ws_url}...")
            with connect(ws_url) as websocket:
                ws_instance = websocket
                print("✅ WebSocket conectado com sucesso!")
                while True:
                    message = websocket.recv()
                    data = json.loads(message)

                    if data.get("type") == "timer_expired":
                        print(f"\n\n🚨 BIP BIP BIP! 🚨")
                        print(f"⏰ {data.get('message')} (Duração: {data.get('duration_seconds')}s)")
                    elif data.get("type") == "play_alarm":
                        print(f"\n🚨 [ALARME] {data.get('message', 'Despertador tocando!')} 🚨")
                        play_alarm_loop()
                    elif data.get("type") == "weather_update":
                        print(f"\n☁️ [DISPLAY] Clima atualizado: {data.get('data')}")
                    elif data.get("type") == "update_wake_word":
                        wake_word = data.get("wake_word", wake_word).lower()
                        print(f"\n\n🔥 [ATUALIZAÇÃO EM TEMPO REAL] Novo Wake Word: {wake_word.upper()} 🔥")
                        print(f"👉 Diga '{wake_word.upper()}' para me chamar!\n")
                    elif data.get("type") == "play_audio":
                        audio_url = data.get("url")
                        print(f"\n🎵 [SATÉLITE] Recebi o comando de tocar um Stream (Live/Música)!")
                        print(f"▶️ Tentando tocar via mplayer/vlc: {audio_url}")
                        try:
                            subprocess.Popen(["mplayer", "-novideo", audio_url],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            try:
                                subprocess.Popen(["cvlc", "--no-video", audio_url],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except FileNotFoundError:
                                print("⚠️ Nenhum player de áudio instalado. Instale: sudo apt install mplayer")
                    elif data.get("type") == "START_STREAM":
                        print(f"\n🎙️ [LIVE AUDIO] Iniciando stream de áudio ao vivo para o Dashboard...")
                        global is_streaming
                        is_streaming = True
                    elif data.get("type") == "STOP_STREAM":
                        print(f"\n🛑 [LIVE AUDIO] Parando stream de áudio ao vivo.")
                        is_streaming = False
                    elif data.get("type") == "SET_ALSA_CAPTURE":
                        val = data.get("value")
                        print(f"🎚️ Ajustando ALSA Capture para {val}%")
                        subprocess.Popen(["amixer", "sset", "Capture", f"{val}%"], stdout=subprocess.DEVNULL)
                        subprocess.Popen(["amixer", "-c", "1", "sset", "Mic", f"{val}%"], stdout=subprocess.DEVNULL)
                    elif data.get("type") == "SET_ALSA_MASTER":
                        val = data.get("value")
                        print(f"🔊 Ajustando ALSA Master para {val}%")
                        subprocess.Popen(["amixer", "sset", "Master", f"{val}%"], stdout=subprocess.DEVNULL)
                    elif data.get("type") == "SET_SOFTWARE_PREAMP":
                        val = float(data.get("value", 1.0))
                        print(f"⚡ Ajustando Multiplicador de Software para {val}x")
                        global SOFTWARE_MULTIPLIER
                        SOFTWARE_MULTIPLIER = val
        except Exception as e:
            print(f"\n[WebSocket] Desconectado: {e}. Tentando reconectar em 5 segundos...")
            ws_instance = None
            time.sleep(5)


def main():
    global vosk_model, vosk_rec, vad, audio_stream

    model_path = os.path.join(os.path.dirname(__file__), "..", "core", "voice", "stt", "models", "vosk-model-small-pt-0.3")

    if not os.path.exists(model_path):
        print(f"❌ Modelo Vosk não encontrado em {model_path}.")
        sys.exit(1)

    print("🧠 Carregando inteligência de Wake Word (Vosk Local Leve)...")
    logging.getLogger("vosk").setLevel(logging.ERROR)

    vosk_model = Model(model_path)
    vosk_rec = KaldiRecognizer(vosk_model, RATE)
    # Baixando a agressividade do VAD de 3 (muito restrito) para 1 (mais sensível à voz de longe)
    vad = webrtcvad.Vad(1)

    if not register_device():
        print("Falha ao registrar. Continuando mesmo assim...")

    threading.Thread(target=websocket_loop, daemon=True).start()
    threading.Thread(target=stream_worker, daemon=True).start()

    print(f"\n🎧 [Satélite da Sala] MODO VOSK (Contínuo Offline) ONLINE e ouvindo silenciosamente...")
    print(f"👉 Diga '{wake_word.upper()}' para me chamar!\n")

    try:
        with sd.InputStream(
            samplerate=RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCKSIZE,
            callback=audio_callback
        ):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando satélite...")
    except Exception as e:
        print(f"Erro no stream de áudio: {e}")
        raise


if __name__ == "__main__":
    print("--- SATELLITE LOCAL (ALFREDO) ---")
    main()
