import numpy as np
from openwakeword.model import Model as OWWModel
from .logger import wake_logger
from .config import config

class WakeWordDetector:
    def __init__(self):
        try:
            self.model = OWWModel()
            wake_logger.info(f"OpenWakeWord carregado para modelo: {config.WAKEWORD_MODEL}")
        except Exception as e:
            wake_logger.error(f"Erro ao carregar modelo OpenWakeWord: {e}")
            self.model = None

    def reset(self):
        """Reseta o estado interno do modelo OWW para evitar re-detecção."""
        if self.model:
            try:
                self.model.reset()
            except Exception as e:
                wake_logger.warning(f"Erro ao resetar modelo OWW: {e}")

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
            
            # Checa se alguma predição passou do threshold (0.5 para evitar
            # falsos positivos em conversa ambiente / TV).
            for model_name, score in predictions.items():
                if score > 0.5:
                    wake_logger.info(f"Wake word detectada! Modelo: {model_name}, Score: {score}")
                    return True
                    
        except Exception as e:
            wake_logger.error(f"Erro durante detecção de wakeword: {e}")
            
        return False
