"""Verifica o estado atual do satélite no M21."""
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

    time.sleep(5)  # dar tempo pro SSH estabilizar

    print("=== PROCESSOS PYTHON ===")
    out = run_ssh(client, "ps aux | grep python | grep -v grep")
    print(out if out else "(nenhum processo python encontrado)")

    print("=== LOG DO SATÉLITE (últimas 200 linhas) ===")
    out = run_ssh(client, "tail -200 /data/data/com.termux/files/home/satellite_loop.log 2>&1")
    print(out if out else "(log vazio ou não encontrado)")

    print("=== ARQUIVOS DE LOG ===")
    out = run_ssh(client, "ls -la /data/data/com.termux/files/home/*.log* /data/data/com.termux/files/home/*.txt* 2>&1")
    print(out if out else "(nenhum)")

    client.close()

if __name__ == "__main__":
    main()
