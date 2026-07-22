"""
Fix M21 v3: switch to small Vosk model + fix PulseAudio persistence.
"""
import paramiko, time, sys

HOST = "192.168.0.40"
PORT = 8022
USER = "admin"
PASSWORD = "1234"

def run(client, cmd, timeout=30):
    for attempt in range(2):
        try:
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
        except Exception as e:
            if attempt == 0: time.sleep(2)
            else: print(f"  timeout: {e}")
    return [], -1

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

# Kill old processes
run(client, "pkill -9 -f android_continuous_satellite 2>/dev/null; pkill -9 -f 'while true' 2>/dev/null; echo killed")

# Upload updated local_stt.py
print("\n=== Upload local_stt.py ===")
transport = paramiko.Transport((HOST, PORT))
transport.connect(username='admin', password='1234')
sftp = paramiko.SFTPClient.from_transport(transport)
proot_base = "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/alfredo-core/devices/android_satellite"
sftp.put(r'C:\Projetos Pessoais\alfredo-core\devices\android_satellite\local_stt.py',
         f'{proot_base}/local_stt.py')
print("Uploaded")
sftp.close()
transport.close()

# Download small Vosk model inside proot
print("\n=== Verificando modelo small ===")
run(client, "proot-distro login ubuntu -- ls /root/alfredo-core/core/voice/stt/models/vosk-model-small-pt-0.3/am/final.mdl 2>/dev/null && echo SMALL_EXISTS || echo SMALL_NEEDED")

run(client, """
if [ ! -d /root/alfredo-core/core/voice/stt/models/vosk-model-small-pt-0.3 ]; then
  echo 'Baixando modelo small (~31MB)...'
  cd /root/alfredo-core/core/voice/stt/models
  wget -q https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
  unzip -q vosk-model-small-pt-0.3.zip
  rm vosk-model-small-pt-0.3.zip
  echo SMALL_DOWNLOADED
else
  echo SMALL_ALREADY_EXISTS
fi
""", timeout=60)

# Now fix PulseAudio to be persistent
print("\n=== Configurar PulseAudio persistente ===")
run(client, """
# Kill old PA, restart with TCP
pulseaudio -k 2>/dev/null; sleep 1
pulseaudio --start \\
  --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" \\
  --load="module-sles-source" \\
  --load="module-sles-sink" \\
  --exit-idle-time=-1
sleep 2
pulseaudio --check && echo PA_OK
""")

# Verify TCP module
run(client, "pactl list modules short | grep tcp || echo TCP_MISSING")

# Start satellite with improved startup (reloads PA if needed)
print("\n=== Iniciando satelite com watchdog de PulseAudio ===")
run(client, """
nohup proot-distro login ubuntu -- bash -c '
export PULSE_SERVER=127.0.0.1
export PYTHONUNBUFFERED=1
cd /root/alfredo-core
while true; do
    echo "[$(date)] (Re)iniciando satelite..."
    python3 -u scripts/android_continuous_satellite.py
    echo "[$(date)] Satelite caiu (exit $?). Tentando novamente em 5s..."
    sleep 5
done
' > /data/data/com.termux/files/home/satellite_loop.log 2>&1 &
echo "PID: $!"
""")

time.sleep(15)

print("\n=== Verificando log ===")
run(client, "cat /data/data/com.termux/files/home/satellite_loop.log")

print("\n=== Processos ===")
run(client, "ps aux | grep -v grep | grep python | head -5")

print("\n=== Memoria ===")
run(client, "free -m")

client.close()
