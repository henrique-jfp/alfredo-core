"""Test audio playback on Android satellite - generates a 440Hz tone."""
import numpy as np
import sounddevice as sd

sr = 48000
t = np.linspace(0, 1, sr)
tone = (np.sin(440 * 2 * np.pi * t) * 30000).astype(np.int16)
print("Playing 440Hz tone for 1 second...")
sd.play(tone, sr)
sd.wait()
print("Tone playback OK!")
