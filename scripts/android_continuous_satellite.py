import os, sys, time, threading, subprocess

try:
    import sounddevice as sd
except ImportError:
    print("Erro: sounddevice não instalado. Execute: pip install sounddevice")
    sys.exit(1)

try:
    import websocket
except ImportError:
    print("Erro: websocket-client não instalado. Execute: pip install websocket-client")
    sys.exit(1)

SERVER_URL = "ws://192.168.0.56:10001"
DEVICE_ID = "android-m21s"
ROOM_ID = "ROOM_LIVING"

RATE = 16000
CHUNK = 960  # 30ms 

ffplay_proc = None
last_byte_time = 0

def on_message(ws, message):
    global ffplay_proc, last_byte_time
    if isinstance(message, bytes):
        last_byte_time = time.time()
        if ffplay_proc is None or ffplay_proc.poll() is not None:
            ffplay_proc = subprocess.Popen(
                ['ffplay', '-nodisp', '-autoexit', '-i', 'pipe:0'],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        try:
            ffplay_proc.stdin.write(message)
            ffplay_proc.stdin.flush()
        except Exception as e:
            print(f"Erro ao passar áudio pro ffplay: {e}")
    else:
        print(f"[Comando do Servidor]: {message}")

def watchdog_audio():
    global ffplay_proc, last_byte_time
    while True:
        time.sleep(0.5)
        if ffplay_proc is not None and ffplay_proc.poll() is None:
            if time.time() - last_byte_time > 1.5:
                try:
                    ffplay_proc.stdin.close()
                except:
                    pass
                ffplay_proc = None

def on_error(ws, error):
    print(f"Erro na conexão: {error}")

def on_close(ws, close_status_code, close_msg):
    print("Conexão perdida. Tentando reconectar em 3 segundos...")

def on_open(ws):
    print(f"Conectado ao servidor {SERVER_URL} com sucesso!")
    print("Abrindo microfone via sounddevice (sem bugs) e iniciando transmissão...")
    
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)
        if ws.keep_running:
            # indata já vem como bytes crus (RawInputStream)
            try:
                ws.send(bytes(indata), opcode=websocket.ABNF.OPCODE_BINARY)
            except:
                pass

    def record_and_send():
        try:
            with sd.RawInputStream(samplerate=RATE, channels=1, dtype='int16', 
                                   blocksize=CHUNK, callback=audio_callback):
                while ws.keep_running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Erro no streaming de microfone: {e}")

    t = threading.Thread(target=record_and_send)
    t.daemon = True
    t.start()

def main():
    print("=========================================")
    print(" ALFREDO CONTINUOUS SATELLITE (TERMUX)   ")
    print("=========================================")
    print(f"Dispositivo: {DEVICE_ID} | Sala: {ROOM_ID}")
    
    watchdog_thread = threading.Thread(target=watchdog_audio)
    watchdog_thread.daemon = True
    watchdog_thread.start()
    
    ws_url = SERVER_URL.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_url}/api/ws/satellite/{DEVICE_ID}"
    
    while True:
        ws = websocket.WebSocketApp(url,
                                  on_open=on_open,
                                  on_message=on_message,
                                  on_error=on_error,
                                  on_close=on_close)
        ws.run_forever()
        time.sleep(3)

if __name__ == "__main__":
    main()
