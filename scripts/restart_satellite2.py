"""Cria script de loop no M21 e inicia o satelite."""
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

# Create the loop script on the device
loop_script = """#!/data/data/com.termux/files/usr/bin/bash
cd /root/alfredo-core || exit 1
export PULSE_SERVER=127.0.0.1
export PYTHONUNBUFFERED=1
while true; do
    echo "[$(date)] (Re)iniciando satelite..."
    python3 -u scripts/android_continuous_satellite.py
    echo "[$(date)] Satelite caiu (exit $?). Reiniciando em 5s..."
    sleep 5
done
"""

# Write the script inside the proot
sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/start_satellite.sh", "w") as f:
    f.write(loop_script)
sftp.close()

print("Script criado no proot.")

# Make it executable and start it inside proot, with output going to Termux home log
# The proot-disto login creates a new proot, but we need it to persist.
# Use nohup in Termux native that calls proot-distro
cmd = (
    'nohup proot-distro login ubuntu -- bash /root/start_satellite.sh '
    '> /data/data/com.termux/files/home/satellite_loop.log 2>&1 &'
)

print("Executando comando de inicializacao...")
chan = client.get_transport().open_session()
chan.settimeout(20)
chan.set_combine_stderr(True)
chan.exec_command(cmd)
result = chan.makefile("r", -1).read()
print(f"Resultado: {result.strip() if result else 'ok'}")

client.close()

print("Aguardando 40s para o boot completo...")
time.sleep(40)

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
chan.exec_command("tail -80 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print("=== LOG ===")
print(chan.makefile("r", -1).read())

chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("ps aux | grep -E '(python|proot)' | grep -v grep")
print("=== PROCESSOS ===")
print(chan2.makefile("r", -1).read())

client.close()
