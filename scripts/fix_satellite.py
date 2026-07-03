import re

with open('/home/pvserver/alfredo-core/scripts/local_satellite.py', 'r') as f:
    content = f.read()

old_block = """                    import subprocess
                    print(f"▶️ Tentando tocar via mplayer/vlc: {audio_url}")
                    try:
                        # Tenta mplayer primeiro (muito comum em Linux sem interface)
                        subprocess.Popen(["mplayer", "-novideo", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except FileNotFoundError:
                        print("mplayer não encontrado. Tentando VLC...")
                        try:
                            subprocess.Popen(["cvlc", "--no-video", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        except FileNotFoundError:
                            print("⚠️ Nenhum player de áudio instalado (mplayer ou vlc). Instale: sudo apt install mplayer")"""

new_block = """                    import subprocess
                    import urllib.request
                    import time
                    import os
                    print(f"▶️ Baixando áudio para tocar: {audio_url}")
                    try:
                        temp_file = f"tmp/ws_audio_{int(time.time())}.wav"
                        os.makedirs("tmp", exist_ok=True)
                        urllib.request.urlretrieve(audio_url, temp_file)
                        subprocess.Popen(["aplay", "-q", temp_file])
                    except Exception as play_e:
                        print(f"⚠️ Erro ao tocar áudio via aplay: {play_e}")"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('/home/pvserver/alfredo-core/scripts/local_satellite.py', 'w') as f:
        f.write(content)
    print("Fix applied successfully!")
else:
    print("Could not find the block to replace!")
