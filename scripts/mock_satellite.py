import os
import wave
import time
import requests
import pyaudio
import audioop
import threading
import json
import webbrowser
from websockets.sync.client import connect

# Configurações do Áudio (Obrigatórias pelo Vosk/Piper)
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "mock_request.wav"
WAVE_RESPONSE_FILENAME = "mock_response.wav"

SERVER_URL = "http://127.0.0.1:10001"
DEVICE_ID = "mock-pc-001"
ROOM_ID = "ROOM_LIVING"

def register_device():
    print("Registrando dispositivo Mock no servidor...")
    url = f"{SERVER_URL}/api/devices/register"
    payload = {
        "device_id": DEVICE_ID,
        "room_id": ROOM_ID,
        "hardware": "mock-python-client",
        "firmware_version": "1.0.0",
        "capabilities": ["microphone", "speaker", "keyboard"]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"Registro OK! Servidor respondeu: {response.json()['message']}")
        return True
    except Exception as e:
        print(f"Falha ao registrar: {e}")
        return False

def record_audio():
    p = pyaudio.PyAudio()
    print("\n* Pressione ENTER para começar a falar (Grava por 5s)...")
    input()
    
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* Ouvindo...")
    frames = []
    
    max_vol = 0
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
        
        # Pega a energia do bloco atual (volume)
        vol = audioop.rms(data, 2)
        if vol > max_vol:
            max_vol = vol

    print("* Parou de ouvir.")
    
    if max_vol < 100:
        print(f"\n[ALERTA!] O volume máximo captado foi muito baixo ({max_vol}).")
        print("Seu microfone parece estar gravando silêncio (ou está muito baixo)!")
        print("Verifique se o Windows está usando o microfone correto como Padrão.\n")
    else:
        print(f"[Volume captado: BOM ({max_vol})]")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return WAVE_OUTPUT_FILENAME

def send_audio_and_play(filename):
    print("Enviando áudio para o servidor...")
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
            
            # Salvar a resposta em disco
            with open(WAVE_RESPONSE_FILENAME, 'wb') as f:
                f.write(response.content)
                
            # Tocar a resposta
            play_audio(WAVE_RESPONSE_FILENAME)
        else:
            print(f"Erro do servidor: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Falha na comunicação com o servidor: {e}")

def play_audio(filename):
    print("* Reproduzindo resposta...")
    wf = wave.open(filename, 'rb')
    p = pyaudio.PyAudio()
    
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
                    
    data = wf.readframes(CHUNK)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(CHUNK)

    stream.stop_stream()
    stream.close()
    p.terminate()
    print("* Reprodução finalizada.")

def start_websocket():
    ws_url = f"ws://127.0.0.1:10001/api/ws/satellite/{DEVICE_ID}"
    try:
        with connect(ws_url) as websocket:
            while True:
                message = websocket.recv()
                data = json.loads(message)
                if data.get("type") == "timer_expired":
                    print(f"\n\n🚨 BIP BIP BIP! 🚨")
                    print(f"⏰ {data.get('message')} (Duração: {data.get('duration_seconds')}s)")
                    print("* Pressione ENTER para começar a falar (Grava por 5s)...")
                elif data.get("type") == "weather_update":
                    print(f"\n[DISPLAY] Clima atualizado via WebSocket: {data.get('data')}")
                elif data.get("type") == "play_audio":
                    audio_url = data.get("url")
                    print(f"\n[SATÉLITE] Recebi o comando de tocar um Stream de Áudio!")
                    print(f"[SATÉLITE] URL do Áudio (Live/Música): {audio_url}")
                    print("[SATÉLITE] Tentando abrir no seu reprodutor/navegador padrão...")
                    # Abre no navegador/VLC nativo do Windows para comprovar que o link funciona
                    webbrowser.open(audio_url)
    except Exception as e:
        print(f"\n[WebSocket] Desconectado ou erro: {e}")

if __name__ == "__main__":
    print("--- MOCK SATELLITE (ALFREDO HOME OS) ---")
    print("NOTA: Certifique-se de que o servidor (FastAPI) está rodando.")
    print("Instale dependências: pip install pyaudio requests")
    
    if register_device():
        # Inicia a thread do WebSocket para receber notificações push (ex: Timers)
        threading.Thread(target=start_websocket, daemon=True).start()
        
        while True:
            audio_file = record_audio()
            
            print("\n[DIAGNÓSTICO] Tocando o que o Python acabou de gravar de você...")
            play_audio(audio_file)
            
            resposta = input("Você ouviu sua voz nitidamente? (s/n): ")
            if resposta.lower() == 's':
                send_audio_and_play(audio_file)
            else:
                print("Se você não ouviu sua voz, o Python gravou silêncio! Vá nas Configurações de Som do Windows e defina o seu HyperX como Dispositivo Padrão de Gravação.")
