"""Testa captura de áudio no M21 e verifica se som entra no microfone."""
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

    time.sleep(3)

    # 1) Check if the proot process has open audio devices
    print("=== PROCESS FD (audio devices) ===")
    out = run_ssh(client, "ls -la /proc/12338/fd/ 2>&1 | head -30", timeout=10)
    print(out)

    # 2) Check PulseAudio connections
    print("=== PACTL INFO ===")
    out = run_ssh(client, "pactl info 2>&1", timeout=10)
    print(out)

    # 3) Check PulseAudio sources/streams
    print("=== PACTL LIST SOURCES ===")
    out = run_ssh(client, "pactl list sources short 2>&1", timeout=10)
    print(out)

    print("=== PACTL LIST SOURCE-OUTPUTS ===")
    out = run_ssh(client, "pactl list source-outputs 2>&1", timeout=10)
    print(out)

    # 4) Try to check if TCP module is loaded
    print("=== PACTL LIST MODULES (grep tcp) ===")
    out = run_ssh(client, "pactl list modules 2>&1 | grep -i tcp; echo '---'; pactl list modules 2>&1 | grep -i native", timeout=10)
    print(out)

    # 5) Check if PULSE_SERVER is set (env of the process)
    print("=== PROOT ENV ===")
    out = run_ssh(client, "cat /proc/12338/environ 2>&1 | tr '\\0' '\\n' | grep -i pulse", timeout=10)
    print(out)

    client.close()

if __name__ == "__main__":
    main()
