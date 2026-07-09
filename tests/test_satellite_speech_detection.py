"""
Testes para o fix de detecção de silêncio no satélite local
(devices/satellite_server/main.py).

Regressão do bug: sem gate de energia, o WebRTC VAD sozinho disparava
"é fala" em ruído de fundo, e silence_frames nunca ultrapassava o
limiar — todo comando esperava o teto rígido de 8s antes de ser
processado, causando a demora de ~6s reportada pelo usuário.

Como o módulo satélite importa libs de hardware (sounddevice, vosk,
webrtcvad, websockets) que podem não estar instaladas em todo ambiente
de CI, o teste pula (skip) graciosamente se o import falhar — mas roda
de verdade no servidor de produção, onde essas libs já estão presentes
(ver requirements.txt).
"""
import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _import_satellite_main_or_none():
    try:
        from devices.satellite_server import main as satellite_main
        return satellite_main
    except Exception:
        return None


satellite_main = _import_satellite_main_or_none()


@unittest.skipIf(
    satellite_main is None,
    "Dependências de áudio (sounddevice/vosk/webrtcvad) indisponíveis neste ambiente."
)
class TestConfirmedSpeechDetection(unittest.TestCase):

    def test_vad_true_but_low_energy_is_not_speech(self):
        """Caso do bug original: VAD dizia 'é fala' em ruído de fundo fraco."""
        result = satellite_main._is_confirmed_speech(
            vad_says_speech=True, rms=500, threshold=2000
        )
        self.assertFalse(result)

    def test_vad_true_and_high_energy_is_speech(self):
        result = satellite_main._is_confirmed_speech(
            vad_says_speech=True, rms=3000, threshold=2000
        )
        self.assertTrue(result)

    def test_vad_false_is_never_speech_even_with_high_energy(self):
        """Um estouro/pico não-vocal com energia alta não deve contar como fala."""
        result = satellite_main._is_confirmed_speech(
            vad_says_speech=False, rms=5000, threshold=2000
        )
        self.assertFalse(result)

    def test_threshold_boundary_is_exclusive(self):
        result = satellite_main._is_confirmed_speech(
            vad_says_speech=True, rms=2000, threshold=2000
        )
        self.assertFalse(result)  # rms precisa ser ESTRITAMENTE maior que o threshold


if __name__ == "__main__":
    unittest.main()