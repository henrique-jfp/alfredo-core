import requests
import wave
import sounddevice as sd
import numpy as np

print("Baixando áudio do TTS...")
url = "http://192.168.0.56:10001/api/voice"
headers = {
    "X-Device-ID": "desktop-satellite-escritorio",
    "X-Room-ID": "ROOM_OFFICE",
    "Authorization": "Bearer mock-token-123"
}

# we need an audio file to send. let's just create a dummy one or send nothing?
# Actually, the endpoint expects audio. Let's create a 1 second silence wav
dummy_wav = "dummy.wav"
with wave.open(dummy_wav, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b'\x00' * 32000)

with open(dummy_wav, 'rb') as f:
    files = {'file': ('audio.wav', f, 'audio/wav')}
    resp = requests.post(url, headers=headers, files=files)

print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    with open("response_test.wav", "wb") as f:
        f.write(resp.content)
    
    with wave.open("response_test.wav", 'rb') as wf:
        data = wf.readframes(wf.getnframes())
        data_np = np.frombuffer(data, dtype=np.int16)
        print(f"Wav recebido com {len(data_np)} samples, {wf.getframerate()}Hz")
        print("Tocando...")
        sd.play(data_np, wf.getframerate())
        sd.wait()
        print("Fim!")
else:
    print(resp.text)
