import threading
import time
from .config import config
from .constants import State, MSG_TYPE_TTS_END, MSG_TYPE_START_STREAM, MSG_TYPE_STOP_STREAM
from .logger import stream_logger, state_logger

class StreamController:
    """
    Mantém os buffers de áudio durante a gravação e controla o flush para o websocket.
    """
    def __init__(self, ws_client):
        self.ws_client = ws_client
        self.audio_buffer = bytearray()
        
    def add_chunk(self, chunk: bytes, live: bool = False):
        if live:
            # Em modo live mic, envia pequenos chunks na hora
            self.ws_client.send_binary(chunk)
        else:
            # Acumula na memória
            self.audio_buffer.extend(chunk)
            
    def flush(self):
        """
        Envia o arquivo inteiro quando termina de falar.
        Se for maior que 8000 bytes, o servidor entende que a frase terminou.
        """
        if len(self.audio_buffer) > 0:
            stream_logger.info(f"Enviando buffer de áudio com {len(self.audio_buffer)} bytes.")
            self.ws_client.send_binary(bytes(self.audio_buffer))
            self.audio_buffer.clear()
            
    def clear(self):
        self.audio_buffer.clear()
