#!/usr/bin/env python3
"""
Diagnóstico de Áudio USB — Alfredo Core
Grava 5 segundos do microfone e analisa o ruído.
"""
import sounddevice as sd
import numpy as np
import wave
import sys
import os

RATE = 16000
CHANNELS = 1
DURATION = 5  # segundos
DTYPE = 'int16'
OUTPUT_FILE = os.path.expanduser("~/alfredo-core/tmp/mic_diagnostic.wav")

print("=" * 60)
print("🎙️  DIAGNÓSTICO DE ÁUDIO USB — ALFREDO CORE")
print("=" * 60)

# 1. Listar dispositivos
print("\n📋 Dispositivos de áudio detectados:")
print(sd.query_devices())
print(f"\n🎯 Device padrão de entrada: {sd.default.device[0]}")

# 2. Gravar
print(f"\n🔴 Gravando {DURATION}s de áudio... (FIQUE EM SILÊNCIO nos primeiros 3s, depois fale)")
try:
    audio = sd.rec(int(DURATION * RATE), samplerate=RATE, channels=CHANNELS, dtype=DTYPE)
    sd.wait()
except Exception as e:
    print(f"❌ Erro ao gravar: {e}")
    sys.exit(1)

samples = audio.flatten()
print(f"✅ Gravado! {len(samples)} amostras ({DURATION}s)")

# 3. Salvar WAV
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
with wave.open(OUTPUT_FILE, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(RATE)
    wf.writeframes(samples.tobytes())
print(f"💾 Salvo em: {OUTPUT_FILE}")

# 4. Análise
float_samples = samples.astype(np.float32)

print("\n" + "=" * 60)
print("📊 ANÁLISE DO ÁUDIO")
print("=" * 60)

# DC Offset
dc_offset = np.mean(float_samples)
print(f"\n🔋 DC Offset: {dc_offset:.1f}")
if abs(dc_offset) > 100:
    print(f"   ⚠️ ALTO! Mic USB tem bias DC significativo ({dc_offset:.0f})")
elif abs(dc_offset) > 30:
    print(f"   ⚡ Moderado. Pode causar pequenos cliques.")
else:
    print(f"   ✅ Normal.")

# RMS (volume geral)
rms = np.sqrt(np.mean(float_samples ** 2))
print(f"\n📢 RMS (volume geral): {rms:.1f}")
if rms < 100:
    print("   ⚠️ MUITO BAIXO! O microfone quase não capta nada.")
elif rms < 500:
    print("   ⚡ Baixo. Voz distante pode não ser captada.")
elif rms > 15000:
    print("   ⚠️ MUITO ALTO! Risco de clipping.")
else:
    print(f"   ✅ Nível adequado.")

# Picos
peak_pos = np.max(float_samples)
peak_neg = np.min(float_samples)
print(f"\n📈 Pico positivo: {peak_pos:.0f} / 32767")
print(f"📉 Pico negativo: {peak_neg:.0f} / -32768")
clipping_count = np.sum((np.abs(float_samples) >= 32000))
if clipping_count > 0:
    print(f"   ⚠️ CLIPPING DETECTADO! {clipping_count} amostras em clipping ({clipping_count/len(samples)*100:.2f}%)")
else:
    print(f"   ✅ Sem clipping.")

# Spikes (mudanças bruscas entre amostras consecutivas)
diffs = np.abs(np.diff(float_samples))
spike_threshold_2k = 2000
spike_threshold_5k = 5000
spike_threshold_10k = 10000
spikes_2k = np.sum(diffs > spike_threshold_2k)
spikes_5k = np.sum(diffs > spike_threshold_5k)
spikes_10k = np.sum(diffs > spike_threshold_10k)
print(f"\n⚡ Spikes (mudanças bruscas entre amostras):")
print(f"   > 2000: {spikes_2k} ({spikes_2k/len(samples)*100:.3f}%)")
print(f"   > 5000: {spikes_5k} ({spikes_5k/len(samples)*100:.3f}%)")
print(f"   > 10000: {spikes_10k} ({spikes_10k/len(samples)*100:.3f}%)")
if spikes_10k > 10:
    print(f"   ⚠️ MUITOS SPIKES! São esses os 'estouros' que você ouve.")
elif spikes_5k > 50:
    print(f"   ⚡ Alguns spikes. Podem causar cliques audíveis.")
else:
    print(f"   ✅ Poucos spikes.")

# Análise por blocos de 100ms (simula o que o callback vê)
block_size = RATE // 10  # 100ms
n_blocks = len(samples) // block_size
block_rms = []
block_peaks = []
for i in range(n_blocks):
    block = float_samples[i*block_size:(i+1)*block_size]
    block_rms.append(np.sqrt(np.mean(block ** 2)))
    block_peaks.append(np.max(np.abs(block)))

block_rms = np.array(block_rms)
block_peaks = np.array(block_peaks)

print(f"\n📦 Análise por blocos de 100ms ({n_blocks} blocos):")
print(f"   RMS mín: {block_rms.min():.1f} | méd: {block_rms.mean():.1f} | máx: {block_rms.max():.1f}")
print(f"   Peak mín: {block_peaks.min():.0f} | méd: {block_peaks.mean():.0f} | máx: {block_peaks.max():.0f}")
print(f"   Variação RMS (std): {block_rms.std():.1f}")

# Ruído de fundo (primeiros 2s = silêncio)
silence_samples = float_samples[:RATE * 2]
silence_rms = np.sqrt(np.mean(silence_samples ** 2))
silence_peak = np.max(np.abs(silence_samples))
print(f"\n🤫 Ruído de fundo (primeiros 2s de silêncio):")
print(f"   RMS: {silence_rms:.1f}")
print(f"   Peak: {silence_peak:.0f}")
if silence_rms > 1000:
    print(f"   ⚠️ RUÍDO DE FUNDO MUITO ALTO! O mic está captando muita interferência.")
elif silence_rms > 300:
    print(f"   ⚡ Ruído moderado. Pode atrapalhar detecção de voz distante.")
else:
    print(f"   ✅ Ruído de fundo aceitável.")

# Frequência dominante do ruído (FFT nos primeiros 2s)
fft = np.abs(np.fft.rfft(silence_samples))
freqs = np.fft.rfftfreq(len(silence_samples), d=1.0/RATE)
# Top 5 frequências
top_indices = np.argsort(fft)[-5:][::-1]
print(f"\n🎵 Frequências dominantes no ruído de fundo:")
for idx in top_indices:
    if freqs[idx] > 0:  # skip DC
        print(f"   {freqs[idx]:.0f} Hz — magnitude {fft[idx]:.0f}")

# Verificar se é ruído de 50/60Hz (rede elétrica)
hz_50_range = fft[(freqs >= 45) & (freqs <= 55)]
hz_60_range = fft[(freqs >= 55) & (freqs <= 65)]
hz_avg = np.mean(fft[freqs > 100])
if len(hz_50_range) > 0 and np.max(hz_50_range) > hz_avg * 5:
    print(f"   ⚠️ INTERFERÊNCIA DE REDE ELÉTRICA (50Hz) detectada!")
if len(hz_60_range) > 0 and np.max(hz_60_range) > hz_avg * 5:
    print(f"   ⚠️ INTERFERÊNCIA DE REDE ELÉTRICA (60Hz) detectada!")

# SNR estimado (voz nos últimos 2s vs silêncio)
voice_samples = float_samples[RATE * 3:]
voice_rms = np.sqrt(np.mean(voice_samples ** 2))
if silence_rms > 0:
    snr = 20 * np.log10(voice_rms / silence_rms) if voice_rms > silence_rms else 0
    print(f"\n📡 SNR estimado (voz vs ruído): {snr:.1f} dB")
    if snr < 6:
        print(f"   ⚠️ SNR PÉSSIMO! A voz mal se distingue do ruído.")
    elif snr < 12:
        print(f"   ⚡ SNR fraco. STT vai ter dificuldade.")
    elif snr < 20:
        print(f"   ✅ SNR aceitável para STT.")
    else:
        print(f"   🎯 SNR excelente!")

print("\n" + "=" * 60)
print("🏁 DIAGNÓSTICO CONCLUÍDO")
print(f"📁 Arquivo WAV salvo em: {OUTPUT_FILE}")
print("=" * 60)
