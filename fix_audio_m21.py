"""Fix audio on M21 proot - install portaudio, configure PulseAudio."""
import paramiko, time, sys

HOST = "192.168.0.40"
PORT = 8022
USER = "admin"
PASSWORD = "1234"

def run(client, cmd, timeout=30):
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
    print("Falhou")
    sys.exit(1)

print("\n=== 1. Matando processo antigo ===")
run(client, "pkill -f android_continuous_satellite 2>/dev/null; pkill -f 'while true.*satellite' 2>/dev/null; echo killed")

print("\n=== 2. Verificando PulseAudio no Termux ===")
run(client, "pulseaudio --check 2>&1; echo EXIT:$?")

print("\n=== 3. Verificando audio devices no Termux ===")
run(client, "pactl info 2>&1 | head -5")
run(client, "pactl list sources short 2>&1")

print("\n=== 4. Verificando socket PulseAudio ===")
run(client, "ls -la /data/data/com.termux/files/usr/var/run/pulse/ 2>/dev/null || echo NO_PULSE_SOCKET_DIR")
run(client, "ls -la $PULSE_SERVER 2>/dev/null; echo PULSE_SERVER=$PULSE_SERVER")

print("\n=== 5. Instalando portaudio no proot ===")
run(client, "proot-distro login ubuntu -- apt install -y libportaudio2 pulseaudio-utils 2>&1 | tail -5", timeout=60)

print("\n=== 6. Testando audio devices dentro do proot ===")
run(client, 'proot-distro login ubuntu -- python3 -c "import sounddevice; print(sounddevice.query_devices())" 2>&1', timeout=30)

print("\n=== 7. Iniciando satelite com PULSE_SERVER configurado ===")
run(client, """
nohup proot-distro login ubuntu -- bash -c '
export PULSE_SERVER=127.0.0.1
cd /root/alfredo-core
while true; do
    echo "[$(date)] (Re)iniciando satelite..."
    python3 scripts/android_continuous_satellite.py
    echo "[$(date)] Satelite caiu. Reiniciando em 5s..."
    sleep 5
done
' > /data/data/com.termux/files/home/satellite_loop.log 2>&1 &
echo "PID: $!"
""")

time.sleep(8)

print("\n=== 8. Verificando log ===")
run(client, "tail -30 /data/data/com.termux/files/home/satellite_loop.log")

print("\n=== 9. Verificando processos ===")
run(client, "ps aux | grep -v grep | grep python | head -5")
run(client, "ps aux | grep -v grep | grep -E 'pulse|audio' | head -5")

client.close()
