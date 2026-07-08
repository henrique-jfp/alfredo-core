import os, sys, time, threading, subprocess
try:
    import pyaudio
except ImportError:
    print("Erro: PyAudio não instalado. Execute: pkg install python-pyaudio")
    sys.exit(1)

try:
    import websocket
except ImportError:
    print("Erro: websocket-client não instalado. Execute: pip install websocket-client")
    sys.exit(1)

SERVER_URL = "ws://192.168.0.56:10001"
DEVICE_ID = "android-m21s"
ROOM_ID = "ROOM_LIVING"

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 960  # 30ms 

audio = pyaudio.PyAudio()

ffplay_proc = None
last_byte_time = 0

def on_message(ws, message):
    global ffplay_proc, last_byte_time
    if isinstance(message, bytes):
        last_byte_time = time.time()
        # Se não há um ffplay rodando, abre um novo recebendo via pipe
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
    """Fecha a entrada do ffplay se o servidor parar de mandar áudio por 1.5s"""
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
    print("Abrindo microfone e iniciando transmissão contínua...")
    
    def record_and_send():
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK)
        try:
            while ws.keep_running:
                # exception_on_overflow=False evita que o PyAudio quebre se o Termux travar um milissegundo
                data = stream.read(CHUNK, exception_on_overflow=False)
                ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            print(f"Erro no streaming de microfone: {e}")
        finally:
            stream.stop_stream()
            stream.close()

    t = threading.Thread(target=record_and_send)
    t.daemon = True
    t.start()

def main():
    print("=========================================")
    print(" ALFREDO CONTINUOUS SATELLITE (TERMUX)   ")
    print("=========================================")
    print(f"Dispositivo: {DEVICE_ID} | Sala: {ROOM_ID}")
    
    # Inicia o vigilante de áudio
    watchdog_thread = threading.Thread(target=watchdog_audio)
    watchdog_thread.daemon = True
    watchdog_thread.start()
    
    # Substitui http/https por ws/wss se o usuário esqueceu
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
