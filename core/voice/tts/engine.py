import os
import wave
import logging
from piper import PiperVoice

logger = logging.getLogger("alfredo.tts")

class TTSEngine:
    def __init__(self, model_path: str = None, config_path: str = None):
        if not model_path:
            model_path = os.path.join(os.getcwd(), "core", "voice", "tts", "models", "pt_BR-faber-medium.onnx")
        if not config_path:
            config_path = f"{model_path}.json"
            
        if not os.path.exists(model_path) or not os.path.exists(config_path):
            raise FileNotFoundError(f"Modelo ou config do PIPER não encontrados em: {model_path}")
            
        logger.info(f"Carregando modelo de voz Piper (Faber) de: {model_path} ...")
        self.voice = PiperVoice.load(model_path, config_path)
        logger.info("Modelo Piper carregado com sucesso.")

    def synthesize_wav(self, text: str, output_filepath: str):
        """
        Gera o áudio a partir do texto e salva no arquivo WAV especificado.
        """
        logger.info(f"Sintetizando áudio para o texto: '{text}'")
        
        with wave.open(output_filepath, "wb") as wav_file:
            # A função synthesize_wav configura automaticamente o formato do WAV
            self.voice.synthesize_wav(text, wav_file)
            
        logger.info(f"Áudio TTS salvo em: {output_filepath}")

# Singleton
_tts_instance = None

def get_tts_engine() -> TTSEngine:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSEngine()
    return _tts_instance
