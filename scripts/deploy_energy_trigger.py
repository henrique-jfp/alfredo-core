"""Deploy controller.py e wakeword.py com energy-based trigger no M21."""
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
    print("Falhou conexao")
    sys.exit(1)

time.sleep(3)

proot_base = "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/alfredo-core"
sftp = client.open_sftp()
sftp.put("devices/android_satellite/controller.py", f"{proot_base}/devices/android_satellite/controller.py")
sftp.put("devices/android_satellite/wakeword.py", f"{proot_base}/devices/android_satellite/wakeword.py")
sftp.close()
print("[OK] controller.py e wakeword.py enviados")

# Kill the satellite (loop will restart)
chan = client.get_transport().open_session()
chan.settimeout(10)
chan.set_combine_stderr(True)
chan.exec_command("pkill -f 'scripts/android_continuous_satellite.py' 2>&1; echo done")
print(f"Kill: {chan.makefile('r', -1).read().strip()}")

client.close()
print("Aguardando 35s para reinicio...")
time.sleep(35)

for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
        break
    except:
        time.sleep(3)
else:
    print("Falhou reconexao")
    sys.exit(1)

time.sleep(10)

chan = client.get_transport().open_session()
chan.settimeout(15)
chan.set_combine_stderr(True)
chan.exec_command("tail -30 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print("=== LOG (ultimas 30 linhas) ===")
print(chan.makefile("r", -1).read())

chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("ps aux | grep python | grep -v grep")
print("=== PROCESSO ===")
print(chan2.makefile("r", -1).read())

client.close()
