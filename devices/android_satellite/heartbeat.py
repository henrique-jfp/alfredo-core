import threading
import time
from .logger import ws_logger
from .config import config

class HeartbeatThread:
    def __init__(self, ws_client):
        self.ws_client = ws_client
        self._stop_event = threading.Event()
        self.thread = None

    def start(self):
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        while not self._stop_event.is_set():
            time.sleep(config.PING_INTERVAL)
            if self.ws_client and self.ws_client.ws and self.ws_client.ws.keep_running:
                try:
                    # Enviar json "ping" ou simplesmente deixar o websocket-client lidar com ping/pong
                    # Aqui implementamos um ping manual em formato JSON que o servidor aceita 
                    # caso o websocket-client demore a falhar em TCP timeout.
                    self.ws_client.send_text('{"type": "PING"}')
                except Exception as e:
                    ws_logger.error(f"Erro ao enviar heartbeat: {e}")
