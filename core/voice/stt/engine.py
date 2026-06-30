import os
import wave
import json
import logging
from vosk import Model, KaldiRecognizer

logger = logging.getLogger("alfredo.stt")

class STTEngine:
    def __init__(self, model_path: str = None):
        if not model_path:
            model_path = os.getenv("VOSK_MODEL_PATH")
            
        if not model_path:
            base_dir = os.path.join(os.getcwd(), "core", "voice", "stt", "models")
            large_path = os.path.join(base_dir, "vosk-model-pt-fb-v0.1.1-20220516_2113")
            small_path = os.path.join(base_dir, "vosk-model-small-pt-0.3")
            
            # O modelo large atual está corrompido, então vamos tentar o small primeiro
            if os.path.exists(small_path):
                model_path = small_path
            else:
                model_path = large_path
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modelo VOSK não encontrado em: {model_path}")
            
        logger.info(f"Carregando modelo VOSK de: {model_path} ...")
        try:
            self.model = Model(model_path)
            logger.info("Modelo VOSK carregado com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao carregar o modelo VOSK {model_path}: {e}")
            if model_path == large_path and os.path.exists(small_path):
                logger.info("Tentando carregar o modelo small como fallback...")
                self.model = Model(small_path)
                logger.info("Modelo VOSK small carregado com sucesso.")
            else:
                raise

    def transcribe_wav(self, audio_filepath: str) -> str:
        """
        Recebe o caminho de um arquivo WAV e retorna o texto transcrito.
        O arquivo deve ser mono, 16kHz, 16bit.
        """
        import audioop
        import warnings
        
        # Ignorar o warning de depreciação do audioop
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            
            wf = wave.open(audio_filepath, "rb")
            
            # Validar formato de áudio para o Vosk
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                raise ValueError("O arquivo de áudio deve ser WAV mono PCM.")
                
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)
            
            # Lê todo o áudio para normalização
            data_all = wf.readframes(wf.getnframes())
            if len(data_all) > 0:
                max_val = audioop.max(data_all, 2)
                # Normaliza apenas se o volume estiver baixo, mas não zerado
                if max_val > 0 and max_val < 25000:
                    factor = 25000.0 / max_val
                    data_all = audioop.mul(data_all, 2, factor)
                    logger.info(f"Áudio normalizado automaticamente. Ganho: {factor:.2f}x (Pico original: {max_val})")
            
            results = []
            chunk_size = 8000 # 4000 frames * 2 bytes
            for i in range(0, len(data_all), chunk_size):
                chunk = data_all[i:i+chunk_size]
                if rec.AcceptWaveform(chunk):
                    part_result = json.loads(rec.Result())
                    results.append(part_result.get("text", ""))
                    
            part_result = json.loads(rec.FinalResult())
            results.append(part_result.get("text", ""))

            # Juntar e limpar texto final
            final_text = " ".join(results).strip()
            logger.info(f"Transcrição concluída: '{final_text}'")
            return final_text

# Singleton opcional para carregar o modelo apenas uma vez durante o tempo de vida do servidor
_stt_instance = None

def get_stt_engine() -> STTEngine:
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = STTEngine()
    return _stt_instance
