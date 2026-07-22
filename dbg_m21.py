"""Debug M21 - check wake word, audio, and satellite state."""
import paramiko, time, sys

HOST = "192.168.0.40"
PORT = 8022
USER = "admin"
PASSWORD = "1234"

def run(client, cmd, timeout=15):
    chan = client.get_transport().open_session()
    chan.settimeout(timeout)
    chan.set_combine_stderr(True)
    chan.exec_command(cmd)
    out = []
    for line in chan.makefile("r", -1):
        try:
            decoded = line.rstrip()
            if decoded:
                out.append(decoded)
                print(f"  {decoded}")
        except:
            pass
    ec = chan.recv_exit_status()
    return out, ec

for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        print("Conectado!")
        break
    except Exception as e:
        print(f"Tentativa {attempt+1}: {e}")
        time.sleep(3)
else:
    print("Falhou - SSH caiu de novo?")
    sys.exit(1)

print("\n=== Log completo desde o inicio ===")
run(client, "cat /data/data/com.termux/files/home/satellite_loop.log")

print("\n=== Verificando se o processo ainda existe ===")
run(client, "ps aux | grep -v grep | grep -E 'python|proot.*satellite' | head -5")

print("\n=== Estado da maquina de estados ===")
run(client, "cat /proc/*/status 2>/dev/null | grep -E 'Name|State' | grep -i python -A1 || echo NO_PROCESS_INFO")

print("\n=== Testando PulseAudio ===")
run(client, "pactl info 2>&1 | head -3")
run(client, "pactl list sources short 2>&1")
run(client, "pactl list modules short 2>&1 | grep -i -E 'tcp|sles|source'")

print("\n=== Memoria ===")
run(client, "free -m")

print("\n=== Verificando wake word no log ===")
run(client, "grep -i -E 'wake|alexa|detect|ouvindo|listen' /data/data/com.termux/files/home/satellite_loop.log")

print("\n=== Verificando se servidor websocket ta conectado ===")
run(client, "grep -c 'Websocket connected' /data/data/com.termux/files/home/satellite_loop.log")

client.close()
