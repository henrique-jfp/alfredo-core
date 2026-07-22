"""Teste interativo de wake word: captura 5s de audio, mostra scores em tempo real."""
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

test_script = b"""import numpy as np
import sounddevice as sd
from openwakeword.model import Model as OWWModel
import time

print("Carregando modelo OWW...")
model = OWWModel()
print("Carregado. Modelos:", list(model.models.keys()))

duration = 5  # 5 segundos
print(f"\\nCapturando {duration}s de audio. FALE 'ALEXA' durante a gravacao!")
print("Iniciando em 3s...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)
print("GRAVANDO!")

rec = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype="int16")
sd.wait()
audio = rec.flatten()
print(f"Audio capturado: {len(audio)} samples, max={np.max(np.abs(audio))}")

# Processar em chunks de 480 (30ms)
max_score = 0
peak_chunk = 0
scores_history = []
for i in range(0, len(audio) - 480, 480):
    chunk = audio[i:i+480]
    pred = model.predict(chunk)
    score = float(pred.get("alexa", 0.0))
    scores_history.append(score)
    if score > max_score:
        max_score = score
        peak_chunk = i // 480
    if score > 0.01:
        print(f"  + Chunk {i//480:3d} ({i/16000:.1f}s): alexa={score:.6f}")

print(f"\\n=== RESUMO ===")
print(f"Max score alexa: {max_score:.6f} no chunk {peak_chunk} ({peak_chunk*480/16000:.1f}s)")
print(f"Media score: {np.mean(scores_history):.6f}")
print(f"Mediana score: {np.median(scores_history):.6f}")
print(f"Score > 0.01: {sum(1 for s in scores_history if s > 0.01)} chunks")
print(f"Score > 0.05: {sum(1 for s in scores_history if s > 0.05)} chunks")
print(f"Score > 0.1: {sum(1 for s in scores_history if s > 0.1)} chunks")
print(f"Score > 0.3: {sum(1 for s in scores_history if s > 0.3)} chunks")

# Salvar audio para analise
audio.tofile("/root/test_alexa.raw")
print(f"\\nAudio salvo em /root/test_alexa.raw")
"""

sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/test_wake_live.py", "w") as f:
    f.write(test_script)
sftp.close()

print("Script escrito. Execute no M21 com:")
print("  proot-distro login ubuntu -- bash -c 'cd /root && PULSE_SERVER=127.0.0.1 python3 test_wake_live.py'")
print()
print("FALE 'ALEXA' em voz alta quando começar a gravar!")

chan = client.get_transport().open_session()
chan.settimeout(90)
chan.set_combine_stderr(True)
chan.exec_command(
    'proot-distro login ubuntu -- bash -c '
    '"cd /root && PULSE_SERVER=127.0.0.1 python3 test_wake_live.py" 2>&1'
)

# Read output line by line
out = chan.makefile("r", -1).read()
print(out)

client.close()
