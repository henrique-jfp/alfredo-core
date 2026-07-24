"""Test sound playback on Android via sounddevice."""
import sys
import numpy as np
import sounddevice as sd

# List audio devices
print("=== Audio Devices ===")
print(sd.query_devices())
print()

# Try to play a 440Hz tone
sr = 48000
duration = 1.0
t = np.linspace(0, duration, int(sr * duration))
tone = (np.sin(440 * 2 * np.pi * t) * 30000).astype(np.int16)

print(f"Playing {duration}s 440Hz tone via default output...")
sd.play(tone, sr)
sd.wait()
print("Playback completed!")
