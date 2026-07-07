"""
Satélite Android (Termux) — modo walkie-talkie.
ENTER para gravar, ENTER para parar, pipeline completo (STT -> NLU -> TTS).
"""
import os, sys
os.environ['PYTHONUNBUFFERED'] = '1'
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(line_buffering=True)

import wave, time, subprocess, threading, tempfile

import requests

SERVER_URL = "http://192.168.0.56:10001"
DEVICE_ID = "android-m21s"
ROOM_ID = "ROOM_LIVING"
AUTH_TOKEN = "secret-token-123"
RATE = 16000


def send_and_play(filepath):
    url = f"{SERVER_URL}/api/voice"
    headers = {
        "X-Device-ID": DEVICE_ID,
        "X-Room-ID": ROOM_ID,
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    try:
        with open(filepath, 'rb') as f:
            t0 = time.time()
            resp = requests.post(url, headers=headers, files={'file': ('audio.wav', f, 'audio/wav')}, stream=True)

        if resp.status_code != 200:
            print(f"Erro {resp.status_code}: {resp.text[:200]}")
            return

        first = False
        player = subprocess.Popen(
            ['ffplay', '-nodisp', '-autoexit', '-i', 'pipe:0'],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for chunk in resp.iter_content(chunk_size=4096):
            if chunk:
                if not first:
                    print(f"Audio em {time.time()-t0:.2f}s!", flush=True)
                    first = True
                player.stdin.write(chunk)
                player.stdin.flush()
        player.stdin.close()
        player.wait()
        print(f"Total: {time.time()-t0:.2f}s", flush=True)
    except Exception as e:
        print(f"Erro: {e}")


def main():
    if not os.path.exists("/system/bin/termux-microphone-record"):
        print("termux-microphone-record nao encontrado. Instale: pkg install termux-api")

    print("=== ALFREDO ANDROID (walkie-talkie) ===")
    print(f"Servidor: {SERVER_URL}")
    print("ENTER -> fale -> ENTER de novo para parar\n")

    while True:
        input("Pressione ENTER para COMECAR a falar...")
        tmp = tempfile.mktemp(suffix=".wav")
        rec = subprocess.Popen([
            "termux-microphone-record", "-d", "-f", tmp,
            "-r", str(RATE), "-c", "1", "-e", "wav"
        ])
        print("Gravando... pressione ENTER para PARAR.", flush=True)
        input()
        rec.terminate()
        rec.wait()

        if not os.path.exists(tmp) or os.path.getsize(tmp) < 2000:
            print("Audio muito curto, ignorando.")
            continue

        print(f"Audio: {os.path.getsize(tmp)} bytes. Enviando...")
        send_and_play(tmp)


if __name__ == "__main__":
    main()
