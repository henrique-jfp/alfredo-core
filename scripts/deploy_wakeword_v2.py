"""Envia wakeword.py (v2 - energia + OWW threshold baixo) e reinicia o satelite."""
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

# Upload wakeword.py
local = "devices/android_satellite/wakeword.py"
remote = "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/alfredo-core/devices/android_satellite/wakeword.py"
sftp = client.open_sftp()
sftp.put(local, remote)
sftp.close()
print("[OK] wakeword.py enviado para proot")

# Kill the satellite - the loop script will restart it
chan = client.get_transport().open_session()
chan.settimeout(10)
chan.set_combine_stderr(True)
chan.exec_command("pkill -f 'python3 -u scripts/android_continuous_satellite.py' 2>&1; echo done")
print(f"Kill: {chan.makefile('r', -1).read().strip()}")

client.close()

print("Aguardando 35s para reinicio completo...")
time.sleep(35)

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
chan.settimeout(20)
chan.set_combine_stderr(True)
chan.exec_command("tail -80 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print("=== LOG ===")
print(chan.makefile("r", -1).read())

chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("ps aux | grep python | grep -v grep")
print("=== PROCESSO ===")
print(chan2.makefile("r", -1).read())

client.close()
