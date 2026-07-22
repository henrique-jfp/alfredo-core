"""
Download small Vosk model inside proot and restart satellite.
"""
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

# Kill old processes
print("Killing old satellite processes...")
run(client, "pkill -9 -f android_continuous_satellite 2>/dev/null; pkill -9 -f 'while true' 2>/dev/null; sleep 2")

# First upload a helper script to the device
print("\nUploading helper script...")
script = """#!/data/data/com.termux/files/usr/bin/bash
# Download small Vosk model inside proot
proot-distro login ubuntu -- bash -c '
set -e
mkdir -p /root/alfredo-core/core/voice/stt/models
cd /root/alfredo-core/core/voice/stt/models
if [ -d vosk-model-small-pt-0.3 ]; then
    echo "SMALL_ALREADY_EXISTS"
    exit 0
fi
echo "Downloading small model..."
wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip
echo "Extracting..."
unzip -q vosk-model-small-pt-0.3.zip
rm vosk-model-small-pt-0.3.zip
echo "DOWNLOAD_COMPLETE"
du -sh vosk-model-small-pt-0.3
'
"""
transport = paramiko.Transport((HOST, PORT))
transport.connect(username='admin', password='1234')
sftp = paramiko.SFTPClient.from_transport(transport)
with sftp.open('/data/data/com.termux/files/home/dl_small.sh', 'w') as f:
    f.write(script)
sftp.close()
transport.close()
print("Helper script uploaded")
run(client, "chmod +x /data/data/com.termux/files/home/dl_small.sh")

# Execute the helper script
print("\nDownloading small model inside proot...")
run(client, "bash /data/data/com.termux/files/home/dl_small.sh", timeout=120)

# Verify
print("\nVerifying model...")
run(client, 'proot-distro login ubuntu -- ls /root/alfredo-core/core/voice/stt/models/vosk-model-small-pt-0.3/am/final.mdl 2>/dev/null && echo "MODEL_OK"')

# Restart PA with TCP
print("\nRestarting PulseAudio...")
run(client, "pulseaudio -k 2>/dev/null; sleep 1")
run(client, 'pulseaudio --start --load="module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1" --load="module-sles-source" --load="module-sles-sink" --exit-idle-time=-1')
time.sleep(2)
run(client, "pulseaudio --check && echo PA_OK || echo PA_FAILED")

# Start satellite
print("\nStarting satellite...")
run(client, """
nohup proot-distro login ubuntu -- bash -c '
export PULSE_SERVER=127.0.0.1
export PYTHONUNBUFFERED=1
cd /root/alfredo-core
while true; do
    echo "[$(date)] (Re)iniciando satelite..."
    python3 -u scripts/android_continuous_satellite.py
    echo "[$(date)] Satelite caiu (exit $?). Reiniciando em 5s..."
    sleep 5
done
' > /data/data/com.termux/files/home/satellite_loop.log 2>&1 &
echo "PID: $!"
""")

time.sleep(20)

print("\nLog:")
run(client, "cat /data/data/com.termux/files/home/satellite_loop.log")

print("\nProcesses:")
run(client, "ps aux | grep -v grep | grep python | awk '{print $2, $8, $3, $4, $11, $12}'")

print("\nMemory:")
run(client, "free -m")

client.close()
