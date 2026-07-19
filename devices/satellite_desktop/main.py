import os
import re
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
import socket
import threading
import logging
import subprocess
from typing import Optional
import urllib.parse

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
WAVE_RESPONSE = "response.mp3"
SERVER_URL = "http://192.168.0.56:10001"
DEVICE_ID = "desktop-satellite-escritorio"
ROOM_ID = "ROOM_OFFICE"

# Constantes de resiliência de rede
WS_CONNECT_TIMEOUT = 10        # timeout máximo para estabelecer conexão TCP
WS_RECV_TIMEOUT = 30           # timeout sem receber dados (evita half-open)
WS_RECONNECT_DELAY = 5         # segundos entre tentativas de reconexão

wake_word = "alfredo"
wake_variants = [
    "alfredo", "alfre", "fredo", "al fredo", "alfred"
]

alarm_process = None
audio_stream: Optional[sd.InputStream] = None
vosk_model: Optional[Model] = None
vosk_rec: Optional[KaldiRecognizer] = None
vad: Optional[webrtcvad.Vad] = None

# Supressão de áudio durante playback para evitar loop (eco)
_is_playing = False
_playback_lock = threading.Lock()
_session_mode = False
_session_lock = threading.Lock()
current_music_process = None

# Variáveis Globais de Estado
is_recording = False
has_spoken = False
silence_frames = 0
recording_buffer = bytearray()
full_audio_buffer = bytearray()
dashcam_buffer = bytearray()
is_streaming = False
stream_queue: queue.Queue = queue.Queue()
audio_queue: queue.Queue = queue.Queue()
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
_notch_x = [0.0, 0.0]
_notch_y = [0.0, 0.0]


def get_rms(data: bytes) -> float:
    samples = array.array('h', data[:len(data) - (len(data) % 2)])
    if not samples:
        return 0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def clean_audio(samples: np.ndarray) -> np.ndarray:
    """Pipeline de limpeza de áudio.
    
    1. Remove DC offset
    2. Notch filter em 434Hz (interferência elétrica do hardware)
    """
    global _notch_x, _notch_y
    audio = samples.astype(np.float32)

    # Etapa 1: Remove DC offset
    audio -= np.mean(audio)

    # Etapa 2: Notch filter biquad em 434Hz (remove zumbido elétrico do notebook)
    # Coeficientes para f0=434Hz, fs=16000Hz, Q=30
    f0 = 434.0
    fs = 16000.0
    Q = 30.0
    w0 = 2.0 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2.0 * Q)
    cos_w0 = np.cos(w0)

    b0 = 1.0 / (1.0 + alpha)
    b1 = -2.0 * cos_w0 / (1.0 + alpha)
    b2 = 1.0 / (1.0 + alpha)
    a1 = -2.0 * cos_w0 / (1.0 + alpha)
    a2 = (1.0 - alpha) / (1.0 + alpha)

    out = np.zeros_like(audio)
    for i in range(len(audio)):
        x = audio[i]
        # Estado inicial
        if i == 0:
            y = b0 * x + b1 * _notch_x[0] + b2 * _notch_x[1] - a1 * _notch_y[0] - a2 * _notch_y[1]
        elif i == 1:
            y = b0 * x + b1 * audio[0] + b2 * _notch_x[0] - a1 * out[0] - a2 * _notch_y[0]
        else:
            y = b0 * x + b1 * audio[i-1] + b2 * audio[i-2] - a1 * out[i-1] - a2 * out[i-2]
        out[i] = y

    # Salva estado para próximo callback
    _notch_x = [audio[-1], audio[-2]] if len(audio) >= 2 else [audio[-1], 0.0]
    _notch_y = [out[-1], out[-2]] if len(out) >= 2 else [out[-1], 0.0]

    return out


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
    print("🔔 Despertador tocando (Simulado no Windows)!")
    # Para o Windows Test Satellite, apenas avisamos no log por enquanto.


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
        "hardware": "windows-desktop-satellite",
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
    global _is_playing
    with _playback_lock:
        _is_playing = True
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
    with _playback_lock:
        _is_playing = False


def _stop_current_music():
    global current_music_process, _is_playing
    if current_music_process:
        try:
            current_music_process.terminate()
            current_music_process.wait(timeout=2)
        except Exception:
            pass
        current_music_process = None
    with _playback_lock:
        _is_playing = False


def _watch_music_process(proc):
    global current_music_process, _is_playing
    try:
        proc.wait()
    except Exception:
        pass
    if current_music_process is proc:
        current_music_process = None
    with _playback_lock:
        _is_playing = False


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
    global full_audio_buffer, dashcam_buffer, SOFTWARE_MULTIPLIER, noise_gate_hold, _session_mode

    # Tratar overflow ao invés de descartar silenciosamente
    if status:
        if status.input_overflow:
            print("⚠️ [AUDIO] Buffer overflow detectado! Áudio pode picotar.", flush=True)
        # Continua processando ao invés de descartar o frame

    # Capturar apenas o PRIMEIRO canal para evitar 'comb filtering' robótico do ALSA downmix
    if indata.shape[1] > 1:
        single_channel = indata[:, 0]
    else:
        single_channel = indata.flatten()
        
    cleaned = single_channel.astype(np.float32)
    
    # Amplificador de software dinâmico
    if SOFTWARE_MULTIPLIER != 1.0:
        cleaned = cleaned * SOFTWARE_MULTIPLIER

    cleaned = soft_clip(cleaned)
    cleaned = cleaned.astype(np.int16)
    bytes_data = cleaned.tobytes()

    # Calibração e gravação movidas para a thread vosk_worker para não travar o áudio
    audio_queue.put_nowait(bytes_data)


def vosk_worker():
    global vosk_rec, is_recording, has_spoken, silence_frames, recording_buffer
    global is_calibrated, calibration_frames, calibration_sum, noise_threshold
    global full_audio_buffer, dashcam_buffer, noise_gate_hold, _session_mode
    
    while True:
        bytes_data = audio_queue.get()
        
        # Calibração inicial (aprox. 2 segundos para ler o chiado do ambiente)
        if not is_calibrated:
            rms = get_rms(bytes_data)
            calibration_sum += rms
            calibration_frames += 1
            required_frames = int((RATE / BLOCKSIZE) * 2.0)
            
            if calibration_frames >= required_frames:
                avg_noise = calibration_sum / calibration_frames
                noise_threshold = avg_noise + 200
                print(f"\\n🎙️ [CALIBRAÇÃO] Ruído de fundo médio: {avg_noise:.1f}")
                print(f"🎙️ [CALIBRAÇÃO] Noise Threshold dinâmico definido para: {noise_threshold:.1f}\\n")
                is_calibrated = True
            continue

        if vosk_rec and not is_recording:
            with _playback_lock:
                if getattr(sys.modules[__name__], '_is_playing', False):
                    continue

            dashcam_buffer.extend(bytes_data)
            if len(dashcam_buffer) > DASHCAM_MAX_BYTES:
                del dashcam_buffer[:-DASHCAM_MAX_BYTES]

            partial = json.loads(vosk_rec.PartialResult())
            partial_text = partial.get('partial', '').strip()
            if partial_text:
                print(f"  VOSK ouvindo: '{partial_text}'", flush=True)

            if vosk_rec.AcceptWaveform(bytes_data):
                result = json.loads(vosk_rec.Result())
                text = result.get('text', '').lower()
                if text.strip() and text != getattr(vosk_worker, "last_print", ""):
                    print(f"  VOSK resultado: '{text}'", flush=True)
                    vosk_worker.last_print = text
                if text.strip() and any(re.search(rf'\b{re.escape(v)}\b', text) for v in wake_variants):
                    print(f"🔔 Palavra de ativação '{wake_word.upper()}' detectada pelo Vosk!", flush=True)
                    _stop_current_music()
                    try:
                        threading.Thread(target=lambda: requests.post(f"{SERVER_URL}/api/tv/control/{ROOM_ID}/mute?state=true", timeout=2), daemon=True).start()
                    except:
                        pass
                    _start_recording()

        if is_streaming:
            stream_queue.put_nowait(bytes_data)

        if is_recording:
            recording_buffer.extend(bytes_data)
            full_audio_buffer.extend(bytes_data)
            
            if vosk_rec:
                if vosk_rec.AcceptWaveform(bytes_data):
                    res = json.loads(vosk_rec.Result())
                    text = res.get('text', '').lower()
                    if any(w in text for w in ["para", "pausa", "chega", "silêncio", "silencio", "desliga", "cala a boca"]):
                        print(f"🛑 [EMERGÊNCIA] Comando detectado ('{text}'). Cortando áudio!", flush=True)
                        has_spoken = True
                        silence_frames = float('inf')
                else:
                    partial = json.loads(vosk_rec.PartialResult())
                    text = partial.get('partial', '').lower()
                    if any(w in text for w in ["para", "pausa", "chega", "silêncio", "silencio", "desliga", "cala a boca"]):
                        print(f"🛑 [EMERGÊNCIA] Comando detectado rápido ('{text}'). Cortando áudio!", flush=True)
                        has_spoken = True
                        silence_frames = float('inf')

            offset = 0
            while offset + 320 <= len(recording_buffer):
                chunk = recording_buffer[offset:offset + 320]
                offset += 320
                is_speech = vad.is_speech(chunk, RATE)
                rms = get_rms(chunk)
                
                if rms < noise_threshold:
                    if noise_gate_hold > 0:
                        noise_gate_hold -= 1
                    else:
                        is_speech = False
                else:
                    noise_gate_hold = NOISE_GATE_HOLD_FRAMES
                    
                if is_speech:
                    has_spoken = True
                    silence_frames = 0
                elif has_spoken:
                    silence_frames += 1
                    
            recording_buffer = bytearray(recording_buffer[offset:])

            total_frames = len(full_audio_buffer) // 320
            max_silence = int(0.7 * RATE / 160)
            timeout_frames = int(20 * RATE / 160) if _session_mode else int(5 * RATE / 160)
            max_total = int(15 * RATE / 160)

            if has_spoken and silence_frames > max_silence:
                print("⏹️ Silêncio detectado. Fim da gravação.", flush=True)
                _finish_recording()
            elif not has_spoken and total_frames > timeout_frames:
                if _session_mode:
                    with _session_lock:
                        _session_mode = False
                    print("⏳ Ninguém respondeu. Saindo do modo mãos-livres.", flush=True)
                else:
                    print("⏳ Ninguém falou nada (5s). Cancelando gravação.", flush=True)
                is_recording = False
                recording_buffer.clear()
                full_audio_buffer.clear()
            elif total_frames > max_total:
                print("⏱️ Tempo máximo de gravação atingido.", flush=True)
                _finish_recording()


def _start_recording():
    global is_recording, recording_buffer, has_spoken, silence_frames, vosk_rec
    global full_audio_buffer, dashcam_buffer, _session_mode
    is_recording = True
    recording_buffer = bytearray()
    
    # Injetando o passado (Dashcam) no buffer final!
    full_audio_buffer = bytearray(dashcam_buffer)
    dashcam_buffer.clear()
    
    # No modo sessão (Alexa), o usuário ainda não falou — aguarda até 5s
    # No modo wake word, o Vosk já detectou "alfredo" — marcamos como fala ativa
    has_spoken = not _session_mode
    silence_frames = 0
    vosk_rec = KaldiRecognizer(vosk_model, RATE)
    stop_alarm()
    
    if _session_mode:
        print("🔴 [MODO MÃOS-LIVRES] Aguardando resposta (sem wake word)...", flush=True)
    else:
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
    last_text = getattr(vosk_worker, "last_print", "")
threading.Thread(target=_send_and_play, args=(buf, last_text), daemon=True).start()


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
        "X-Vosk-Text": urllib.parse.quote(vosk_text), # Encoding p/ caracteres especiais no header HTTP
        "Authorization": "Bearer mock-token-123"
    }
    try:
        with open(WAVE_OUTPUT, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            t_send = time.time()
            response = requests.post(url, headers=headers, files=files, stream=True)

        if response.status_code == 200:
            first_byte_received = False

            global _is_playing
            with _playback_lock:
                _is_playing = True

            import uuid
            import glob
            
            # Limpa arquivos MP3 antigos para não lotar o disco
            for old_mp3 in glob.glob(os.path.join(os.path.dirname(__file__), "response_*.mp3")):
                try: os.remove(old_mp3)
                except: pass

            response_mp3 = os.path.join(os.path.dirname(__file__), f"response_{uuid.uuid4().hex[:6]}.mp3")
            with open(response_mp3, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        if not first_byte_received:
                            ttfb = time.time() - t_send
                            print(f"🔊 Áudio iniciado em {ttfb:.2f} segundos!", flush=True)
                            first_byte_received = True
                        f.write(chunk)
            
            # Tocar o áudio MP3 nativamente no Windows com playsound
            try:
                from playsound import playsound
                print(f"▶️ Iniciando reprodução do MP3 no Windows...", flush=True)
                playsound(response_mp3)
                print(f"⏹️ Reprodução finalizada.", flush=True)
            except Exception as e:
                print(f"Erro ao tocar áudio nativamente: {e}", flush=True)

            total_time = time.time() - t_start
            print(f"✅ Interação concluída. Tempo total: {total_time:.2f} segundos.", flush=True)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Falha na comunicação com o servidor: {e}")
    finally:
        with _playback_lock:
            _is_playing = False
        # Auto-unmute TV
        try:
            threading.Thread(target=lambda: requests.post(f"{SERVER_URL}/api/tv/control/{ROOM_ID}/mute?state=false", timeout=2), daemon=True).start()
        except:
            pass

    # Modo mãos-livres: se houver sessão ativa, grava a próxima resposta sem wake word
    try:
        status_resp = requests.get(
            f"{SERVER_URL}/api/session-status",
            params={"room_id": ROOM_ID},
            timeout=2
        )
        if status_resp.status_code == 200:
            if status_resp.json().get("active") and not is_recording:
                with _session_lock:
                    _session_mode = True
                print("🎯 Sessão ativa — modo mãos-livres ativado!", flush=True)
                _start_recording()
            else:
                with _session_lock:
                    _session_mode = False
    except Exception:
        with _session_lock:
            _session_mode = False


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
    global ws_instance, is_streaming, wake_word, _is_playing
    ws_url = f"ws://{SERVER_URL.replace('http://', '').replace('https://', '')}/api/ws/satellite/{DEVICE_ID}"

    while True:
        try:
            print(f"🔄 Tentando conectar ao WebSocket em {ws_url}...")
            with connect(ws_url, open_timeout=WS_CONNECT_TIMEOUT) as websocket:
                ws_instance = websocket
                print("✅ WebSocket conectado com sucesso!")
                while True:
                    try:
                        message = websocket.recv(timeout=WS_RECV_TIMEOUT)
                    except TimeoutError:
                        print("[WS] Timeout sem mensagens — conexão ainda ativa")
                        continue

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
                        global current_music_process
                        _stop_current_music()
                        try:
                            current_music_process = subprocess.Popen(["mplayer", "-novideo", audio_url],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            try:
                                current_music_process = subprocess.Popen(["cvlc", "--no-video", audio_url],
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except FileNotFoundError:
                                print("⚠️ Nenhum player de áudio instalado. Instale: sudo apt install mplayer")
                        if current_music_process:
                            with _playback_lock:
                                _is_playing = True
                            threading.Thread(target=_watch_music_process, args=(current_music_process,), daemon=True).start()
                    elif data.get("type") == "stop_audio":
                        print("\n🛑 [SATÉLITE] Parando música atual.")
                        _stop_current_music()
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
        except (OSError, ConnectionError, TimeoutError) as e:
            print(f"\n[WebSocket] Falha na conexão ({ws_url}): {e}. Tentando reconectar em {WS_RECONNECT_DELAY}s...")
            ws_instance = None
            time.sleep(WS_RECONNECT_DELAY)
        except Exception as e:
            print(f"\n[WebSocket] Erro inesperado: {e}. Reconectando em {WS_RECONNECT_DELAY}s...")
            ws_instance = None
            time.sleep(WS_RECONNECT_DELAY)


def main():
    global vosk_model, vosk_rec, vad, audio_stream

    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "core", "voice", "stt", "models", "vosk-model-small-pt-0.3")

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
    threading.Thread(target=vosk_worker, daemon=True).start()

    print(f"\n🎧 [Satélite do Escritório] MODO VOSK (Contínuo Offline) ONLINE e ouvindo silenciosamente...")
    print(f"👉 Diga '{wake_word.upper()}' para me chamar!\n")

    try:
        input_device = sd.default.device[0]
        if input_device is None:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get('max_input_channels', 0) > 0 and ('ps3' in dev.get('name', '').lower() or 'eye' in dev.get('name', '').lower()):
                    input_device = idx
                    print(f"🎙️ [ÁUDIO] PS3 Eye encontrado: [{idx}] {dev['name']}", flush=True)
                    break
            if input_device is None:
                for idx, dev in enumerate(devices):
                    if dev.get('max_input_channels', 0) > 0:
                        input_device = idx
                        print(f"⚠️ [ÁUDIO] Usando primeiro input disponível: [{idx}] {dev['name']}", flush=True)
                        break

        native_channels = sd.query_devices(input_device)['max_input_channels']
            
        print(f"🎙️ Capturando áudio em {native_channels} canais nativos para evitar distorção de downmix do PortAudio...")
        
        with sd.InputStream(
            device=input_device,
            samplerate=RATE,
            channels=native_channels,
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
