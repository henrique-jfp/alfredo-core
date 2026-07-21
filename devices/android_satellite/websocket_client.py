import websocket
import threading
from typing import Callable, Optional
from .logger import ws_logger
from .reconnect import ReconnectStrategy

class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.ws: Optional[websocket.WebSocketApp] = None
        
        # Callbacks
        self.on_open_cb = None
        self.on_message_cb = None
        self.on_close_cb = None
        self.on_error_cb = None
        
        self._run_thread = None
        self._disconnecting = False

    def connect(self):
        self._disconnecting = False
        ws_logger.info(f"Conectando ao servidor: {self.url}")
        
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        
        self._run_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self._run_thread.start()

    def disconnect(self):
        self._disconnecting = True
        if self.ws:
            self.ws.close()
            self.ws = None

    def _on_open(self, ws):
        ws_logger.info("Conexão WebSocket estabelecida.")
        if self.on_open_cb:
            self.on_open_cb()

    def _on_message(self, ws, message):
        if self.on_message_cb:
            self.on_message_cb(message)

    def _on_error(self, ws, error):
        ws_logger.error(f"Erro no WebSocket: {error}")
        if self.on_error_cb:
            self.on_error_cb(error)

    def _on_close(self, ws, close_status_code, close_msg):
        ws_logger.warning("Conexão WebSocket fechada.")
        if self.on_close_cb:
            self.on_close_cb(close_status_code, close_msg)

    def send_text(self, text: str):
        if self.ws and self.ws.keep_running:
            try:
                self.ws.send(text)
            except Exception as e:
                ws_logger.error(f"Erro ao enviar texto: {e}")

    def send_binary(self, data: bytes):
        if self.ws and self.ws.keep_running:
            try:
                self.ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                ws_logger.error(f"Erro ao enviar binário: {e}")
