"""Verifica estado final do satellite apos deploy."""
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

# Check processes
chan = client.get_transport().open_session()
chan.settimeout(10)
chan.set_combine_stderr(True)
chan.exec_command("ps aux | grep python | grep -v grep")
print("=== PROCESSOS ===")
print(chan.makefile("r", -1).read())

# Check log size and tail
chan2 = client.get_transport().open_session()
chan2.settimeout(10)
chan2.set_combine_stderr(True)
chan2.exec_command("wc -l /data/data/com.termux/files/home/satellite_loop.log")
print("=== LOG SIZE ===")
print(chan2.makefile("r", -1).read())

chan3 = client.get_transport().open_session()
chan3.settimeout(15)
chan3.set_combine_stderr(True)
chan3.exec_command("tail -20 /data/data/com.termux/files/home/satellite_loop.log")
out3 = chan3.makefile("r", -1).read()
print("=== TAIL ===")
print(out3)

client.close()
