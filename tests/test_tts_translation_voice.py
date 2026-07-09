"""
Testes para o fix de gênero de voz nas traduções do TTSEngine.
"""
import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.voice.tts.engine import TTSEngine


class TestTranslationVoiceGender(unittest.TestCase):

    def test_male_assistant_voice_gets_male_translation_voice(self):
        engine = TTSEngine(voice_name="pt-BR-AntonioNeural")
        self.assertFalse(engine._is_current_voice_female())
        self.assertEqual(engine._get_translation_voice("en-US"), "en-US-GuyNeural")

    def test_female_assistant_voice_gets_female_translation_voice(self):
        engine = TTSEngine(voice_name="pt-BR-FranciscaNeural")
        self.assertTrue(engine._is_current_voice_female())
        self.assertEqual(engine._get_translation_voice("en-US"), "en-US-AriaNeural")

    def test_unknown_locale_falls_back_to_current_voice(self):
        engine = TTSEngine(voice_name="pt-BR-AntonioNeural")
        self.assertEqual(engine._get_translation_voice("xx-XX"), "pt-BR-AntonioNeural")

    def test_reload_voice_updates_gender_detection(self):
        engine = TTSEngine(voice_name="pt-BR-FranciscaNeural")
        self.assertEqual(engine._get_translation_voice("es-ES"), "es-ES-ElviraNeural")

        engine.reload_voice("pt-BR-AntonioNeural")
        self.assertEqual(engine._get_translation_voice("es-ES"), "es-ES-AlvaroNeural")


if __name__ == "__main__":
    unittest.main()