import os
import wave
import time
import requests
import subprocess
import threading
import json
import webbrowser
from websockets.sync.client import connect
import sys
import signal

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

SERVER_URL = "http://127.0.0.1:10001"
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
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Registro OK! Servidor respondeu: {response.json()['message']}")
        
        # Aproveita para buscar o Wake Word atual salvo no banco
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
        print(f"Falha ao registrar: {e}")
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
    print("🔊 Reproduzindo resposta...")
    try:
        subprocess.run(['aplay', '-q', filename], check=True)
    except Exception as e:
        print(f"Erro ao reproduzir áudio com aplay: {e}")

def start_websocket():
    ws_url = f"ws://127.0.0.1:10001/ws/satellite/{DEVICE_ID}"
    try:
        with connect(ws_url) as websocket:
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
                    # No Linux sem interface gráfica, tocar via VLC/mplayer seria o ideal
                    # Aqui usamos subprocess para tentar rodar um player de áudio do sistema
                    import subprocess
                    print(f"▶️ Tentando tocar via mplayer/vlc: {audio_url}")
                    try:
                        # Tenta mplayer primeiro (muito comum em Linux sem interface)
                        subprocess.Popen(["mplayer", "-novideo", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except FileNotFoundError:
                        print("mplayer não encontrado. Tentando VLC...")
                        try:
                            subprocess.Popen(["cvlc", "--no-video", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            print("⚠️ Nenhum player de áudio instalado (mplayer ou vlc). Instale: sudo apt install mplayer")
    except Exception as e:
        print(f"\n[WebSocket] Desconectado: {e}")

def record_and_send():
    RECORD_SECONDS = 5
    print("\n🔴 [GRAVANDO] Pode falar o comando! (Gravando por 5 segundos...)")
    
    try:
        subprocess.run(['play', '-q', '-n', 'synth', '0.15', 'sine', '880'], check=False)
    except:
        pass
    
    cmd = [
        'arecord', '-q', '-d', str(RECORD_SECONDS),
        '-f', 'S16_LE', '-c', '1', '-r', str(RATE), 
        WAVE_OUTPUT_FILENAME
    ]
    try:
        subprocess.run(cmd, check=True)
        print("⏹️ [GRAVAÇÃO CONCLUÍDA] Processando comando...")
        
        url = f"{SERVER_URL}/api/voice"
        headers = {
            "X-Device-ID": DEVICE_ID,
            "X-Room-ID": ROOM_ID,
            "Authorization": "Bearer mock-token-123"
        }
        
        with open(WAVE_OUTPUT_FILENAME, 'rb') as f:
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
        print(f"Erro ao gravar com arecord ou enviar: {e}")

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
    
    record_cmd = ['arecord', '-q', '-f', 'S16_LE', '-c', '1', '-r', str(RATE), '-t', 'raw']
    process = None
    
    try:
        process = subprocess.Popen(record_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        while True:
            data = process.stdout.read(CHUNK)
            if len(data) == 0:
                continue
                
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get('text', '').lower()
                
                if WAKE_WORD in text:
                    print(f"🔔 Palavra de ativação '{WAKE_WORD.upper()}' detectada pelo Vosk!")
                    
                    stop_alarm()
                    process.terminate()
                    process.wait()
                    
                    record_and_send()
                    
                    process = subprocess.Popen(record_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    print(f"\n🎧 Voltando a dormir... Diga '{WAKE_WORD.upper()}' para chamar novamente.")
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
