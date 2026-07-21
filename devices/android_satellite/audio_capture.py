import ctypes.util
import time
import threading
from .config import config
from .logger import audio_logger

# HACK PARA O TERMUX: O Android esconde as bibliotecas do sistema,
# então enganamos o Python para apontar direto para o arquivo do Termux.
import os

original_find_library = ctypes.util.find_library

def patch_find_library(name):
    if name == 'portaudio':
        # Verifica se estamos rodando no Termux nativo (e não no proot Ubuntu)
        if "PREFIX" in os.environ and "/com.termux/" in os.environ["PREFIX"]:
            termux_path = '/data/data/com.termux/files/usr/lib/libportaudio.so'
            if os.path.exists(termux_path):
                return termux_path
    return original_find_library(name)

ctypes.util.find_library = patch_find_library

try:
    import sounddevice as sd
except Exception as e:
    audio_logger.error(f"Erro ao importar sounddevice: {e}. Execute: pip install sounddevice e pkg install portaudio -y")
    sd = None

class AudioCapture:
    def __init__(self, audio_callback):
        self.audio_callback = audio_callback
        self.stream = None
        self._stop_event = threading.Event()
        self.thread = None

    def _internal_callback(self, indata, frames, time_info, status):
        if status:
            audio_logger.warning(f"Audio status: {status}")
        
        # indata é numpy array. Convert para bytes
        audio_bytes = bytes(indata)
        self.audio_callback(audio_bytes)

    def start(self):
        if not sd:
            audio_logger.error("Sounddevice não carregado, impossível capturar áudio.")
            return

        self._stop_event.clear()
        
        def record_thread():
            try:
                audio_logger.info("Iniciando captura de áudio...")
                with sd.RawInputStream(
                    samplerate=config.RATE, 
                    channels=config.CHANNELS, 
                    dtype=config.DTYPE, 
                    blocksize=config.CHUNK, 
                    callback=self._internal_callback
                ):
                    while not self._stop_event.is_set():
                        time.sleep(0.1)
                audio_logger.info("Captura de áudio finalizada.")
            except Exception as e:
                audio_logger.error(f"Erro no stream de microfone: {e}")
        
        self.thread = threading.Thread(target=record_thread, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
