import os
import logging
from groq import Groq

logger = logging.getLogger("alfredo.stt")

class STTEngine:
    def __init__(self, model_path: str = None):
        # O model_path é mantido na assinatura para retrocompatibilidade, mas não é usado.
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY não encontrada. A transcrição de voz (Whisper) falhará.")
        
        try:
            self.client = Groq(api_key=api_key)
            logger.info("Motor STT (Groq Whisper Large V3) inicializado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao inicializar o cliente Groq para STT: {e}")
            raise

    def transcribe_wav(self, audio_filepath: str) -> str:
        """
        Recebe o caminho de um arquivo WAV e retorna o texto transcrito usando a API da Groq (Whisper).
        """
        if not os.path.exists(audio_filepath):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_filepath}")
            
        logger.info(f"Enviando áudio para Groq Whisper API: {audio_filepath}")
        try:
            with open(audio_filepath, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                  file=(os.path.basename(audio_filepath), file.read()),
                  model="whisper-large-v3",
                  response_format="text",
                  language="pt" # Força o português mas ele entende perfeitamente termos em inglês juntos
                )
            
            # A API retorna o texto diretamente quando response_format="text"
            final_text = str(transcription).strip().lower()
            
            # Remove pontuações comuns que o Whisper gosta de adicionar (vírgulas, pontos)
            import string
            final_text = final_text.translate(str.maketrans('', '', string.punctuation))
            
            logger.info(f"Transcrição concluída via Groq Whisper: '{final_text}'")
            return final_text
            
        except Exception as e:
            logger.error(f"Erro na transcrição via Groq Whisper: {e}")
            return ""

# Singleton opcional para carregar o modelo apenas uma vez durante o tempo de vida do servidor
_stt_instance = None

def get_stt_engine() -> STTEngine:
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = STTEngine()
    return _stt_instance
