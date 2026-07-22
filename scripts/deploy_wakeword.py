"""Envia wakeword.py atualizado para o M21 e reinicia o satelite."""
import paramiko
import time
import sys

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

    local_path = "devices/android_satellite/wakeword.py"

    # Upload to proot container rootfs (where the running code is)
    remote_proot = "/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/alfredo-core/devices/android_satellite/wakeword.py"
    sftp = client.open_sftp()
    sftp.put(local_path, remote_proot)
    sftp.close()
    print("[OK] wakeword.py enviado para proot")

    # 2) Kill the satellite process (loop restarts it automatically)
    chan = client.get_transport().open_session()
    chan.settimeout(10)
    chan.set_combine_stderr(True)
    chan.exec_command("kill $(pgrep -f 'android_continuous_satellite.py' | head -1) 2>&1; echo 'kill sent'")
    result = chan.makefile("r", -1).read()
    print(f"Kill: {result.strip()}")

    client.close()
    print("Aguardando 15s para o satelite reiniciar com o novo wakeword.py...")
    time.sleep(15)

    # 3) Reconnect and check logs
    for attempt in range(5):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
            break
        except Exception as e:
            print(f"Reconexao tentativa {attempt+1}: {e}")
            time.sleep(3)
    else:
        print("Falhou ao reconectar")
        sys.exit(1)

    time.sleep(5)

    chan = client.get_transport().open_session()
    chan.settimeout(15)
    chan.set_combine_stderr(True)
    chan.exec_command("tail -50 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
    print("=== LOG APOS REINICIO ===")
    print(chan.makefile("r", -1).read())

    # Check if process is running
    chan2 = client.get_transport().open_session()
    chan2.settimeout(10)
    chan2.set_combine_stderr(True)
    chan2.exec_command("ps aux | grep python | grep -v grep | awk '{print $2, $6/1024, $11}'")
    print("=== PROCESSOS ===")
    print(chan2.makefile("r", -1).read())

    client.close()

if __name__ == "__main__":
    main()
