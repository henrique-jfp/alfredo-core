import sounddevice as sd
import numpy as np
import time

print("Dispositivos de áudio:")
print(sd.query_devices())

print("\nDispositivo padrão de saída:")
print(sd.default.device[1])

print("\nGerando beep de 1 segundo (440Hz)...")
fs = 16000
duration = 1.0  # seconds
t = np.linspace(0, duration, int(fs * duration), False)
# Generate a 440 Hz sine wave
data = 0.5 * np.sin(2 * np.pi * 440 * t)

print("Tocando beep...")
sd.play(data, fs)
sd.wait()
print("Pronto!")
