"""Verifica PulseAudio e dispositivos de áudio no M21."""
import paramiko
import time
import sys

def run_ssh(client, cmd, timeout=15):
    chan = client.get_transport().open_session()
    chan.settimeout(timeout)
    chan.set_combine_stderr(True)
    chan.exec_command(cmd)
    return chan.makefile("r", -1).read()

def main():
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
        print("Falhou ao conectar")
        sys.exit(1)

    time.sleep(5)

    # PulseAudio - check if running via proot
    print("=== PULSEAUDIO (proot) ===")
    out = run_ssh(client, "pulseaudio --version 2>&1 || echo 'not found'")
    print(out)

    print("=== PULSEAUDIO (Termux native) ===")
    out = run_ssh(client, "pulseaudio --version 2>&1 || echo 'not found'", timeout=10)
    print(out)

    print("=== PROOT PA INFO ===")
    out = run_ssh(client, "cat /proc/12338/status 2>&1 | grep -E '(Name|Pid|VmRSS|Threads|State)'", timeout=10)
    print(out)

    print("=== PORTA 4713 ===")
    out = run_ssh(client, "ss -tlnp | grep 4713 2>&1 || netstat -tlnp 2>&1 | grep 4713 || echo 'port 4713 not listening'", timeout=10)
    print(out)

    print("=== AUDIO DEVICES (proot) ===")
    out = run_ssh(client, "cat /proc/12338/fd 2>&1 | head -20 ; pacmd list-sources 2>&1 | head -30", timeout=10)
    print(out)

    print("=== SATELLITE LOG (native) ===")
    out = run_ssh(client, "tail -100 /data/data/com.termux/files/home/satellite_native.log 2>&1", timeout=10)
    print(out)

    client.close()

if __name__ == "__main__":
    main()
