import subprocess
import wave
import struct

def test_mic():
    # Kill the satellite temporarily so it releases the microphone
    subprocess.run(["pkill", "-f", "local_satellite.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "devices/satellite_server/main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "arecord"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print("Gravando do microfone por 3 segundos...")
    filename = "test_mic.wav"
    subprocess.run(["arecord", "-d", "3", "-f", "S16_LE", "-c", "1", "-r", "16000", filename], check=False)
    
    try:
        with wave.open(filename, "rb") as w:
            n_frames = w.getnframes()
            data = w.readframes(n_frames)
            # S16_LE
            samples = struct.unpack(f"<{n_frames}h", data)
            max_amp = max(samples)
            min_amp = min(samples)
            print(f"Resultado da Gravação:")
            print(f"- Amplitude Máxima: {max_amp}")
            print(f"- Amplitude Mínima: {min_amp}")
            
            if max_amp < 10 and min_amp > -10:
                print("ERRO: O microfone gravou apenas silêncio total. Problema de hardware ou driver no Ubuntu.")
            else:
                print("OK: O microfone está captando som!")
    except Exception as e:
        print(f"Erro ao analisar áudio: {e}")

if __name__ == "__main__":
    test_mic()
