"""Testa transcricao Vosk para ver se reconhece 'alexa' ou 'liga TV'."""
import paramiko
import time
import sys

for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
        break
    except:
        time.sleep(3)
else:
    print("Falhou")
    sys.exit(1)

time.sleep(3)

test = b"""import vosk, json, numpy as np, sounddevice as sd, time

model = vosk.Model("/root/alfredo-core/core/voice/stt/models/vosk-model-small-pt-0.3")
rec = vosk.KaldiRecognizer(model, 16000)

print("Gravando 5s... FALE: 'ALEXA, LIGAR A TELEVISAO DA SALA'")
print("Iniciando em 3...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)
print("GRAVANDO!")

audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
audio = audio.flatten().tobytes()

# Processa em chunks de 4000 (250ms)
offset = 0
while offset < len(audio):
    chunk = audio[offset:offset+8000]
    if len(chunk) < 8000:
        chunk = chunk + b'\\x00\\x00' * (4000 - len(chunk)//2)
    rec.AcceptWaveform(chunk)
    offset += 8000

result = json.loads(rec.FinalResult())
print("\\nTranscricao final:", result)
print("Texto:", result.get("text", ""))

# Test with partial results
rec2 = vosk.KaldiRecognizer(model, 16000)
rec2.SetWords(True)
for i in range(0, len(audio), 480):
    chunk = audio[i:i+480]
    if len(chunk) < 960:
        break
    rec2.AcceptWaveform(chunk)
    partial = json.loads(rec2.PartialResult())
    text = partial.get("partial", "")
    if text:
        print(f"  Parcial ({i/16000:.1f}s): {text}")

result2 = json.loads(rec2.FinalResult())
print("\\nFinal com words:", result2.get("text", ""))
"""

sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/test_vosk_transcribe.py", "w") as f:
    f.write(test)
sftp.close()

print("Testando transcricao Vosk...")
print("FALE O COMANDO QUANDO COMEÇAR A GRAVAR!")
chan = client.get_transport().open_session()
chan.settimeout(90)
chan.set_combine_stderr(True)
chan.exec_command(
    'proot-distro login ubuntu -- bash -c '
    '"cd /root && PULSE_SERVER=127.0.0.1 python3 test_vosk_transcribe.py" 2>&1'
)
out = chan.makefile("r", -1).read()
print(out)
client.close()
