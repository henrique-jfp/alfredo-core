"""Mata o satellite dentro do proot e verifica o restart."""
import paramiko
import time
import sys

def run_ssh(client, cmd, timeout=15):
    chan = client.get_transport().open_session()
    chan.settimeout(timeout)
    chan.set_combine_stderr(True)
    chan.exec_command(cmd)
    return chan.makefile("r", -1).read()

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

# Kill from inside proot
print("Matando processo dentro do proot...")
out = run_ssh(client, 'proot-distro login ubuntu -- bash -c "pkill -f android_continuous_satellite; echo DONE"', timeout=20)
print(f"Resultado: {out.strip()}")
time.sleep(2)

# Force kill if still alive
out = run_ssh(client, 'proot-distro login ubuntu -- bash -c "pgrep -f android_continuous_satellite; echo ---"', timeout=10)
print(f"Ainda vivo: {out.strip()}")

client.close()
print("\nAguardando 20s para o loop reiniciar...")
time.sleep(20)

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

time.sleep(3)

print("\n=== LOG ATUAL ===")
out = run_ssh(client, "tail -60 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
print(out)

print("\n=== PROCESSOS ===")
out = run_ssh(client, "ps aux | grep -E '(python|proot)' | grep -v grep")
print(out)

client.close()
