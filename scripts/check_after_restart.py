"""Verifica logs apos restart do satelite com novo wakeword.py."""
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

time.sleep(20)

chan = client.get_transport().open_session()
chan.settimeout(15)
chan.set_combine_stderr(True)
chan.exec_command("tail -60 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print("=== LOG ===")
print(chan.makefile("r", -1).read())

chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("ps aux | grep python | grep -v grep")
print("=== PROCESSO ===")
print(chan2.makefile("r", -1).read())

client.close()
