import numpy as np
from openwakeword.model import Model as OWWModel
from .logger import wake_logger
from .config import config

class WakeWordDetector:
    def __init__(self):
        try:
            self.model = OWWModel(
                wakeword_model_paths=[config.WAKEWORD_MODEL]
            )
            wake_logger.info(f"OpenWakeWord carregado para modelo: {config.WAKEWORD_MODEL}")
        except Exception as e:
            wake_logger.error(f"Erro ao carregar modelo OpenWakeWord: {e}")
            self.model = None

    def detect(self, audio_chunk: bytes) -> bool:
        """
        Analisa um chunk de áudio em busca da wake word.
        Retorna True se detectado.
        """
        if not self.model:
            return False
            
        try:
            # openwakeword requer numpy array de np.int16
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)
            
            # Predict
            predictions = self.model.predict(audio_np)
            
            # Checa se alguma predição passou do threshold (ex: > 0.4)
            for model_name, score in predictions.items():
                if score > 0.4:
                    wake_logger.info(f"Wake word detectada! Modelo: {model_name}, Score: {score}")
                    return True
                    
        except Exception as e:
            wake_logger.error(f"Erro durante detecção de wakeword: {e}")
            
        return False
