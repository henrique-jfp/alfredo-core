"""Testa o wake word detector diretamente no M21."""
import paramiko
import time
import sys

for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
        break
    except Exception as e:
        print(f"Tentativa {attempt+1}: {e}")
        time.sleep(3)
else:
    print("Falhou")
    sys.exit(1)

time.sleep(3)

# Write test script to proot
test_script = b"""import numpy as np
import sounddevice as sd
import time
from openwakeword.model import Model as OWWModel

print("Carregando modelo OWW...")
model = OWWModel()
print("Modelo carregado.")

# Test with silence (zeros)
print("\\nTeste com silencio (zeros):")
silence = np.zeros(480, dtype=np.int16)
pred = model.predict(silence)
print(f"  Predictions: {pred}")
for k, v in pred.items():
    print(f"  {k}: {v:.6f}")

# Test with random noise
print("\\nTeste com ruido aleatorio:")
noise = np.random.randint(-1000, 1000, 480, dtype=np.int16)
pred = model.predict(noise)
print(f"  Predictions: {pred}")
for k, v in pred.items():
    print(f"  {k}: {v:.6f}")

# Test with real audio capture
print("\\nCapturando audio real (3s)...")
rec = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
audio = rec.flatten()
print(f"  Audio shape: {audio.shape}, max: {np.max(np.abs(audio))}")

# Process first chunk
chunk = audio[:480]
pred = model.predict(chunk)
print(f"  First chunk predictions: {pred}")
for k, v in pred.items():
    print(f"  {k}: {v:.6f}")

# Process all chunks and track max score
max_score = 0
for i in range(0, len(audio) - 480, 480):
    chunk = audio[i:i+480]
    pred = model.predict(chunk)
    score = max(pred.values())
    if score > max_score:
        max_score = score
        if score > 0.1:
            print(f"  High score at chunk {i//480}: {score:.6f} - {pred}")

print(f"\\nMax score em 3s de audio: {max_score:.6f}")
print("Model reset test:")
model.reset()
pred = model.predict(silence)
print(f"  After reset: {pred}")
"""

sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/test_wake.py", "w") as f:
    f.write(test_script)
sftp.close()

print("Script escrito. Executando teste de wake word...")

chan = client.get_transport().open_session()
chan.settimeout(60)
chan.set_combine_stderr(True)
chan.exec_command(
    'proot-distro login ubuntu -- bash -c '
    '"cd /root && PULSE_SERVER=127.0.0.1 python3 test_wake.py" 2>&1'
)
out = chan.makefile("r", -1).read()
print(out)

client.close()
