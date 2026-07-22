"""Reinicia o satelite no M21 dentro do proot."""
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

# First check if PulseAudio TCP is running
chan = client.get_transport().open_session()
chan.settimeout(10)
chan.set_combine_stderr(True)
chan.exec_command("pactl list modules 2>&1 | grep tcp || echo 'TCP module not found'")
print("=== PULSEAUDIO TCP ===")
print(chan.makefile("r", -1).read())

# Start satellite in background inside proot
# Using nohup and disown to survive SSH disconnection
cmd = (
    'nohup proot-distro login ubuntu -- bash -c \''
    'export PULSE_SERVER=127.0.0.1 '
    'export PYTHONUNBUFFERED=1 '
    'cd /root/alfredo-core && '
    'while true; do '
    'echo "[$(date)] (Re)iniciando satelite..."; '
    'python3 -u scripts/android_continuous_satellite.py; '
    'echo "[$(date)] Satelite caiu (exit $?). Reiniciando em 5s..."; '
    'sleep 5; '
    'done\' '
    '> /data/data/com.termux/files/home/satellite_loop.log 2>&1 &'
)

# Actually, better approach: start proot in background from Termux
# and redirect its output to the log file
cmd2 = (
    'nohup /data/data/com.termux/files/usr/bin/proot-distro login ubuntu '
    '-- bash -c '
    '"export PULSE_SERVER=127.0.0.1 '
    'export PYTHONUNBUFFERED=1 '
    'cd /root/alfredo-core && '
    'while true; do '
    'echo \\"[\\$(date)] (Re)iniciando satelite...\\"; '
    'python3 -u scripts/android_continuous_satellite.py; '
    'echo \\"[\\$(date)] Satelite caiu (exit \\$?). Reiniciando em 5s...\\"; '
    'sleep 5; '
    'done" '
    '> /data/data/com.termux/files/home/satellite_loop.log 2>&1 &'
)

print("Iniciando satelite em background...")
chan2 = client.get_transport().open_session()
chan2.settimeout(20)
chan2.set_combine_stderr(True)
chan2.exec_command(cmd2)
result = chan2.makefile("r", -1).read()
print(f"Resultado: {result.strip() if result else '(vazio)'}")

client.close()

print("Aguardando 30s para o boot completo...")
time.sleep(30)

# Reconnect and check
for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
        break
    except Exception as e:
        print(f"Reconexao {attempt+1}: {e}")
        time.sleep(3)
else:
    print("Falhou reconexao")
    sys.exit(1)

time.sleep(5)

chan = client.get_transport().open_session()
chan.settimeout(15)
chan.set_combine_stderr(True)
chan.exec_command("tail -60 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print("=== LOG ===")
print(chan.makefile("r", -1).read())

chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("ps aux | grep -E '(python|proot)' | grep -v grep")
print("=== PROCESSOS ===")
print(chan2.makefile("r", -1).read())

client.close()
