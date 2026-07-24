import webrtcvad
from .config import config
from .logger import vad_logger
from .utils import get_rms

class VoiceActivityDetector:
    def __init__(self):
        self.vad = webrtcvad.Vad(config.VAD_MODE)
        # O threshold de ruído poderia ser dinâmico ou calibrado, por enquanto mantemos fixo.
        self.noise_threshold = 600.0 
        vad_logger.info(f"VAD Inicializado (Modo: {config.VAD_MODE})")

    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Retorna True se o áudio contiver voz humana com energia mínima (RMS).
        WebRTC VAD funciona com chunks de 10, 20 ou 30ms a 16kHz (ex: 320, 640 ou 960 bytes).
        """
        try:
            # VAD verifica o espectro
            vad_says_speech = self.vad.is_speech(audio_chunk, config.RATE)
            # RMS verifica a energia para evitar falsos positivos do VAD em ruído constante
            rms = get_rms(audio_chunk)
            
            is_confirmed = vad_says_speech and rms > self.noise_threshold
            return is_confirmed
            
        except Exception as e:
            vad_logger.error(f"Erro no VAD: {e}")
            return False
