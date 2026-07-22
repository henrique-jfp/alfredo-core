"""Testa se o audio capturado tem sinal nao-zero no M21."""
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
test_script = b"""import sounddevice as sd
import numpy as np
import time

print("Teste de captura de audio...")
duration = 2
rec = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
print("Shape:", rec.shape)
print("Max:", np.max(np.abs(rec)))
print("Mean abs:", np.mean(np.abs(rec)))
print("Non-zero samples:", np.count_nonzero(rec), "/", rec.size)
print("First 20 samples:", rec[:20].flatten())
"""

sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/test_audio.py", "w") as f:
    f.write(test_script)
sftp.close()

print("Script de teste escrito. Executando...")

chan = client.get_transport().open_session()
chan.settimeout(30)
chan.set_combine_stderr(True)
chan.exec_command(
    'proot-distro login ubuntu -- bash -c '
    '"cd /root && PULSE_SERVER=127.0.0.1 python3 test_audio.py" 2>&1'
)
out = chan.makefile("r", -1).read()
print(out)

client.close()
