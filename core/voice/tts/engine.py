import os
import wave
import logging
import urllib.request
from piper import PiperVoice

logger = logging.getLogger("alfredo.tts")

class TTSEngine:
    def __init__(self, voice_name: str = "pt_BR-faber-medium"):
        self.current_voice_name = voice_name
        self.voice = None
        self._load_voice(voice_name)
        
    def _load_voice(self, voice_name: str):
        """Baixa (se necessário) e carrega o modelo do Piper."""
        models_dir = os.path.join(os.getcwd(), "core", "voice", "tts", "models")
        os.makedirs(models_dir, exist_ok=True)
        
        model_path = os.path.join(models_dir, f"{voice_name}.onnx")
        config_path = f"{model_path}.json"
        
        # Se não existe, baixa do HuggingFace
        if not os.path.exists(model_path) or not os.path.exists(config_path):
            logger.info(f"Modelo {voice_name} não encontrado. Baixando do HuggingFace (aprox 30MB)...")
            
            parts = voice_name.split("-")
            prefix = parts[0] # ex: pt_BR
            speaker = parts[1] # ex: faber
            quality = parts[2] # ex: medium
            base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/{prefix}/{speaker}/{quality}/{voice_name}.onnx"
            
            try:
                urllib.request.urlretrieve(base_url, model_path)
                urllib.request.urlretrieve(f"{base_url}.json", config_path)
                logger.info("Download concluído com sucesso!")
            except Exception as e:
                logger.error(f"Falha ao baixar modelo {voice_name}: {e}")
                raise e
                
        logger.info(f"Carregando modelo de voz Piper ({voice_name}) ...")
        self.voice = PiperVoice.load(model_path, config_path)
        self.current_voice_name = voice_name
        logger.info("Modelo Piper carregado com sucesso.")
        
    def reload_voice(self, voice_name: str):
        """Troca a voz ativa em tempo real."""
        if self.current_voice_name != voice_name:
            self._load_voice(voice_name)

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
