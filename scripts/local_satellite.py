import os
import sys

# Forçar stdout/stderr sem buffer para logs em tempo real com nohup
os.environ['PYTHONUNBUFFERED'] = '1'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

import wave
import time
import requests
import subprocess
import threading
import json
import webbrowser
from websockets.sync.client import connect
import signal
import platform

alarm_process = None

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

try:
    from vosk import Model, KaldiRecognizer
except ImportError:
    print("Vosk não encontrado. Rode: pip install vosk")
    sys.exit(1)

# Configurações do Áudio
CHUNK = 4096
RATE = 16000
WAVE_OUTPUT_FILENAME = "request.wav"
WAVE_RESPONSE_FILENAME = "response.wav"

SERVER_URL = "http://pvserver:10001"
DEVICE_ID = "server-satellite-sala"
ROOM_ID = "ROOM_LIVING"

WAKE_WORD = "alfredo" # Padrão, mas será sobrescrito pelo backend

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
            # Sync Wake Word
            try:
                settings_res = requests.get(f"{SERVER_URL}/api/dashboard/settings", timeout=3)
                if settings_res.status_code == 200:
                    settings_data = settings_res.json()
                    if "assistant_name" in settings_data:
                        global WAKE_WORD
                        WAKE_WORD = settings_data["assistant_name"].lower()
                        print(f"📡 Wake Word sincronizado com o servidor: {WAKE_WORD.upper()}")
            except Exception as e:
                print(f"Aviso: Não foi possível sincronizar o Wake Word: {e}")
            return True
        except Exception as e:
            print(f"Falha ao registrar (tentativa {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)  # exponential backoff
    return False


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
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            latency = time.time() - start_time
            print(f"Resposta recebida em {latency:.2f} segundos!")
            
            with open(WAVE_RESPONSE_FILENAME, 'wb') as f:
                f.write(response.content)
                
            play_audio(WAVE_RESPONSE_FILENAME)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Falha na comunicação com o servidor: {e}")

def play_audio(filename):
    print("🔊 Reproduzindo resposta (volume amplificado)...", flush=True)
    try:
        # Amplifica o áudio em 3x com sox antes de tocar
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

def start_websocket():
    ws_url = f"ws://{SERVER_URL.replace('http://', '').replace('https://', '')}/api/ws/satellite/{DEVICE_ID}"
    while True:
        try:
            print(f"Tentando conectar ao WebSocket em {ws_url}...")
            with connect(ws_url) as websocket:
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
                        global WAKE_WORD
                        WAKE_WORD = data.get("wake_word", WAKE_WORD).lower()
                        print(f"\n\n🔥 [ATUALIZAÇÃO EM TEMPO REAL] Novo Wake Word: {WAKE_WORD.upper()} 🔥")
                        print(f"👉 Diga '{WAKE_WORD.upper()}' para me chamar!\n")
                    elif data.get("type") == "play_audio":
                        audio_url = data.get("url")
                        print(f"\n🎵 [SATÉLITE] Recebi o comando de tocar um Stream (Live/Música)!")
                        print(f"▶️ Tentando tocar via mplayer/vlc: {audio_url}")
                        try:
                            subprocess.Popen(["mplayer", "-novideo", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            print("mplayer não encontrado. Tentando VLC...")
                            try:
                                subprocess.Popen(["cvlc", "--no-video", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            except FileNotFoundError:
                                print("⚠️ Nenhum player de áudio instalado (mplayer ou vlc). Instale: sudo apt install mplayer")
                    elif data.get("type") == "START_STREAM":
                        print(f"\n🎙️ [LIVE AUDIO] Iniciando stream de áudio ao vivo para o Dashboard...")
                        global stream_active, stream_thread
                        stream_active = True
                        stream_thread = threading.Thread(target=stream_audio_loop, args=(websocket,), daemon=True)
                        stream_thread.start()
                    elif data.get("type") == "STOP_STREAM":
                        print(f"\n🛑 [LIVE AUDIO] Parando stream de áudio ao vivo.")
                        stream_active = False
        except Exception as e:
            print(f"\n[WebSocket] Desconectado: {e}. Tentando reconectar em 5 segundos...")
            time.sleep(5)


def get_live_audio_cmd():
    """Retorna o comando para capturar áudio bruto continuamente via stdout.
    Formato: 16kHz, Mono, 16-bit PCM (raw).
    SEM filtros, SEM processamento — apenas captura pura.
    """
    if platform.system() == "Windows":
        mic_device = os.getenv("FFMPEG_MIC_DEVICE", "audio=Microfone (default)")
        return [
            "ffmpeg", "-y", "-f", "dshow", "-i", mic_device,
            "-acodec", "pcm_s16le", "-ar", str(RATE), "-ac", "1",
            "-f", "s16le", "-flush_packets", "1", "-"
        ]
    else:
        # Linux: arecord puro, sem filtros, sem ffmpeg
        cmd = ['arecord', '-q', '-f', 'S16_LE', '-c', '1', '-r', str(RATE), '-t', 'raw']
        if os.getenv('EXTERNAL_MIC_DEVICE'):
            cmd.extend(['-D', os.getenv('EXTERNAL_MIC_DEVICE')])
        return cmd


stream_active = False
stream_thread = None

def stream_audio_loop(ws):
    """Captura áudio e envia ao Dashboard via WebSocket. Usa o MESMO formato do Vosk (arecord puro)."""
    global stream_active
    cmd = get_live_audio_cmd()
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while stream_active:
            data = proc.stdout.read(4096)
            if data:
                ws.send(data)
            else:
                time.sleep(0.01)
    except Exception as e:
        print(f"Erro no streaming: {e}")
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except:
                proc.kill()


import array
import math

def get_rms(chunk):
    samples = array.array('h', chunk)
    if not samples:
        return 0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def record_and_send():
    try:
        import webrtcvad
    except ImportError:
        print("❌ webrtcvad não encontrado. Execute: pip install webrtcvad")
        return
        
    vad = webrtcvad.Vad(3) # 3 = most aggressive filtering
    
    print("\n🔴 [GRAVANDO] Ouvindo comando...", flush=True)
    
    try:
        subprocess.run(['play', '-q', '-n', 'synth', '0.15', 'sine', '880'], check=False)
    except:
        pass
        
    cmd = get_live_audio_cmd()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    audio_buffer = bytearray()
    has_spoken = False
    silence_frames = 0
    # frames of 20ms at 16kHz 16-bit mono = 320 bytes
    max_silence_frames = int(1.5 * 16000 * 2 / 320) # 1.5s of silence
    timeout_frames = int(5 * 16000 * 2 / 320) # 5s timeout if no speech
    MAX_RECORD_FRAMES = int(15 * 16000 * 2 / 320)
    total_frames = 0
    
    try:
        while True:
            chunk = proc.stdout.read(320)
            if len(chunk) < 320:
                continue
                
            audio_buffer.extend(chunk)
            total_frames += 1
            
            is_speech = vad.is_speech(chunk, RATE)
            rms = get_rms(chunk)
            
            # Se o áudio é muito baixo (ex: ruído estático/vento de fundo), forçamos como silêncio, 
            # mesmo que o WebRTC VAD ache que é voz por causa de frequências parecidas.
            # O ruído de fundo medido foi ~1600.
            if rms < 2000:
                is_speech = False
                
            if is_speech:
                has_spoken = True
                silence_frames = 0
            else:
                if has_spoken:
                    silence_frames += 1
                    
            if has_spoken and silence_frames > max_silence_frames:
                print(f"⏹️ Silêncio detectado (RMS < 2000 ou VAD). Fim da gravação.", flush=True)
                break
                
            if not has_spoken and total_frames > timeout_frames:
                print(f"⏳ Ninguém falou nada (5s). Cancelando gravação.", flush=True)
                proc.kill()
                return
                
            if total_frames > MAX_RECORD_FRAMES:
                print(f"⏳ Tempo máximo atingido. Cortando.", flush=True)
                break
    except Exception as e:
        print(f"Erro na gravação VAD: {e}")
    finally:
        try:
            proc.stdout.close()
        except:
            pass
        proc.kill()
        proc.wait()
        
    print(f"\n⏹️ [VAD] Tamanho do áudio: {len(audio_buffer)} bytes. Enviando...", flush=True)
    t_start = time.time()
    
    try:
        with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(RATE)
            wf.writeframes(audio_buffer)
            
        url = f"{SERVER_URL}/api/voice"
        headers = {
            "X-Device-ID": DEVICE_ID,
            "X-Room-ID": ROOM_ID,
            "Authorization": "Bearer mock-token-123"
        }
        
        with open(WAVE_OUTPUT_FILENAME, 'rb') as f:
            files = {'file': ('audio.wav', f, 'audio/wav')}
            t_send = time.time()
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            t_response = time.time()
            server_latency = t_response - t_send
            total_latency = t_response - t_start
            print(f"✅ [RESPOSTA] Servidor: {server_latency:.1f}s | Total: {total_latency:.1f}s", flush=True)
            with open(WAVE_RESPONSE_FILENAME, 'wb') as f:
                f.write(response.content)
            play_audio(WAVE_RESPONSE_FILENAME)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Erro ao salvar/enviar áudio: {e}")

def main_loop():
    model_path = os.path.join(os.path.dirname(__file__), "..", "core", "voice", "stt", "models", "vosk-model-small-pt-0.3")
    
    if not os.path.exists(model_path):
        print(f"❌ Modelo Vosk não encontrado em {model_path}.")
        sys.exit(1)

    print("🧠 Carregando inteligência de Wake Word (Vosk Local Leve)...")
    import logging
    logging.getLogger("vosk").setLevel(logging.ERROR)
    
    model = Model(model_path)
    recognizer = KaldiRecognizer(model, RATE)
    
    print(f"\n🎧 [Satélite da Sala] MODO VOSK (Contínuo Offline) ONLINE e ouvindo silenciosamente...")
    print(f"👉 Diga '{WAKE_WORD.upper()}' para me chamar!\n")
    
    record_cmd = get_live_audio_cmd()
    process = None
    
    try:
        process = subprocess.Popen(record_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        while True:
            if stream_active:
                if process:
                    try:
                        process.stdout.close()
                    except:
                        pass
                    process.kill()
                    process.wait()
                    process = None
                time.sleep(0.5)
                continue

            if process is None or process.poll() is not None:
                process = subprocess.Popen(record_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                continue
                
            data = process.stdout.read(CHUNK)
            if len(data) == 0:
                time.sleep(0.1)
                if process:
                    try:
                        process.stdout.close()
                    except:
                        pass
                    process.kill()
                    process.wait()
                    process = None
                continue
                
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').lower()
                
                if text.strip():
                    print(f"🗣️ [VOSK DEBUG] Ouvi: '{text}'", flush=True)
                
                wake_variants = [
                    WAKE_WORD, "alfre", "fredo", "frente", "alfredo",
                    "al fredo", "alfredou", "alfreu", "alfrente", "alfred"
                ]
                
                wake_detected = any(variant in text for variant in wake_variants)
                
                if wake_detected:
                    print(f"🔔 Palavra de ativação '{WAKE_WORD.upper()}' detectada pelo Vosk!", flush=True)
                    stop_alarm()
                    
                    if process:
                        try:
                            process.stdout.close()
                        except:
                            pass
                        process.kill()
                        process.wait()
                        process = None
                        
                    record_and_send()
                    
                    recognizer = KaldiRecognizer(model, RATE)
                    print(f"\n🎧 Voltando a dormir... Diga '{WAKE_WORD.upper()}' para chamar novamente.", flush=True)
            else:
                pass
    except KeyboardInterrupt:
        print("\nEncerrando satélite...")
    except Exception as e:
        print(f"Erro no loop de áudio: {e}")
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    print("--- SATELLITE LOCAL (ALFREDO) ---")
    if register_device():
        threading.Thread(target=start_websocket, daemon=True).start()
        main_loop()
