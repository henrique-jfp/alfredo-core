import paramiko
import traceback
import sys
import time
import os

def main():
    hostname = "192.168.0.40"
    port = 8022
    username = "admin"
    password = "1234"

    out = ""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        out += "Connecting...\n"
        client.connect(hostname, port=port, username=username, password=password, timeout=10)
        out += "Connected!\n"

        def run(cmd):
            nonlocal out
            out += f"RUNNING: {cmd}\n"
            stdin, stdout, stderr = client.exec_command(cmd)
            out += "OUT: " + stdout.read().decode() + "\n"
            out += "ERR: " + stderr.read().decode() + "\n"

        run("proot-distro login ubuntu -- bash -c 'pkill -9 -f python'")
        time.sleep(1)
        run("proot-distro login ubuntu -- bash -c 'cd ~/alfredo-core ; git checkout -- scripts/start_satellite_loop.sh'")
        run("proot-distro login ubuntu -- bash -c 'cd ~/alfredo-core ; git pull origin main'")
        
        client.exec_command("proot-distro login ubuntu -- bash -c 'cd ~/alfredo-core ; nohup bash scripts/start_satellite_loop.sh > satellite_out.log 2>&1 &'")
        out += "Started satellite in background!\n"
        time.sleep(4)

        run("proot-distro login ubuntu -- bash -c 'ps aux | grep python'")
        run("proot-distro login ubuntu -- bash -c 'tail -n 30 ~/alfredo-core/satellite_out.log'")
        
        client.close()
    except Exception as e:
        out += f"Exception: {e}\n{traceback.format_exc()}"
        
    log_path = os.path.join(r"c:\Projetos Pessoais\alfredo-core", "android_logs.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(out)

if __name__ == "__main__":
    main()
