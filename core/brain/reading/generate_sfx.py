"""
Gerador de efeitos sonoros placeholder para o Alfredo Reads.

Execute este script para criar arquivos MP3 placeholder no diretório
assets/sfx/. Cada arquivo é um tom simples de 1-3 segundos que pode
ser substituído por efeitos reais depois.

Uso:
    python -m core.brain.reading.generate_sfx
"""
import os
import sys

def generate_placeholders():
    """Gera arquivos MP3 placeholder para todos os efeitos do vocabulário."""
    from pydub import AudioSegment
    from pydub.generators import Sine

    sfx_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ))), "assets", "sfx")
    os.makedirs(sfx_dir, exist_ok=True)

    effects = {
        "thunder":      (80,  3000),   # Tom grave, 3s
        "wind":         (200, 3000),   # Tom médio-baixo, 3s
        "door_creak":   (400, 2000),   # Tom médio, 2s
        "footsteps":    (300, 2000),   # Tom médio, 2s
        "rain":         (600, 4000),   # Tom médio-alto, 4s
        "fire_crackle": (500, 3000),   # Tom médio, 3s
        "bell":         (800, 1500),   # Tom alto, 1.5s
        "suspense":     (150, 3000),   # Tom grave, 3s
    }

    for name, (freq, duration_ms) in effects.items():
        filepath = os.path.join(sfx_dir, f"{name}.mp3")
        if os.path.exists(filepath):
            print(f"  ⏭️  {name}.mp3 já existe — pulando")
            continue

        # Gera tom simples com fade in/out para evitar clique
        tone = Sine(freq).to_audio_segment(duration=duration_ms)
        tone = tone.fade_in(100).fade_out(200)
        # Volume baixo (-20dB) para não assustar quando misturado com voz
        tone = tone - 20

        tone.export(filepath, format="mp3", bitrate="48k")
        print(f"  ✅ {name}.mp3 criado ({duration_ms}ms, {freq}Hz)")

    print(f"\n📁 Efeitos salvos em: {sfx_dir}")


if __name__ == "__main__":
    generate_placeholders()
