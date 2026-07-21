import threading
import time
from .config import config
from .constants import State, MSG_TYPE_TTS_END
from .logger import ws_logger, audio_logger, player_logger
from .protocol import build_identify_payload, decode_json
from .state_machine import StateMachine
from .websocket_client import WebSocketClient
from .reconnect import ReconnectStrategy
from .heartbeat import HeartbeatThread
from .audio_capture import AudioCapture
from .audio_player import AudioPlayer
from .wakeword import WakeWordDetector
from .vad import VoiceActivityDetector
from .streaming import StreamController

class Controller:
    def __init__(self):
        self.sm = StateMachine()
        self.reconnect_strategy = ReconnectStrategy()
        
        self.ws = WebSocketClient(f"{config.SERVER_URL}/api/ws/satellite/{config.DEVICE_ID}")
        self.ws.on_open_cb = self.on_ws_open
        self.ws.on_message_cb = self.on_ws_message
        self.ws.on_close_cb = self.on_ws_close
        self.ws.on_error_cb = self.on_ws_error
        
        self.heartbeat = HeartbeatThread(self.ws)
        self.stream_ctrl = StreamController(self.ws)
        
        self.audio_player = AudioPlayer()
        self.wake_detector = WakeWordDetector()
        self.vad = VoiceActivityDetector()
        
        # Audio Capture
        self.audio_capture = AudioCapture(self.on_audio_chunk)
        
        # Variáveis de controle de silêncio
        self.silence_frames = 0
        self.max_silence_frames = int((config.SILENCE_TIMEOUT_MS / 1000.0) / (config.CHUNK / config.RATE))
        self.is_speaking = False

    def register_device(self):
        import urllib.request
        import json
        
        # O config.SERVER_URL tem o formato ws://192.168.0.56:10001
        http_url = config.SERVER_URL.replace("ws://", "http://").replace("wss://", "https://")
        register_url = f"{http_url}/api/devices/register"
        
        payload = {
            "device_id": config.DEVICE_ID,
            "room_id": config.ROOM_ID,
            "hardware": "Android Phone (Proot)",
            "firmware_version": "1.1.0",
            "capabilities": ["mic", "speaker"]
        }
        
        try:
            req = urllib.request.Request(
                register_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            urllib.request.urlopen(req, timeout=5)
            ws_logger.info("Dispositivo registrado na API REST com sucesso.")
        except Exception as e:
            ws_logger.warning(f"Não foi possível registrar na API (pode não aparecer no dashboard): {e}")

    def start(self):
        self.sm.transition(State.CONNECTING)
        self.register_device()
        self.ws.connect()
        # Inicia captura continuamente. O que faremos com os chunks dependerá do estado.
        self.audio_capture.start()
        
        # Main loop para manter vivo e lidar com reconexões
        while True:
            try:
                time.sleep(1)
                
                # Gerencia reconexão se necessário
                if self.sm.get_state() == State.RECONNECTING:
                    self.reconnect_strategy.wait()
                    self.sm.transition(State.CONNECTING)
                    self.ws.connect()
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                ws_logger.error(f"Erro no main loop do controller: {e}")

    def on_ws_open(self):
        self.reconnect_strategy.reset()
        self.sm.transition(State.CONNECTED)
        
        # Identifica-se pro servidor
        self.ws.send_text(build_identify_payload(config.DEVICE_ID, config.ROOM_ID))
        
        self.heartbeat.start()
        self.sm.transition(State.LISTENING)

    def on_ws_close(self, status, msg):
        self.heartbeat.stop()
        self.sm.transition(State.RECONNECTING)

    def on_ws_error(self, error):
        self.heartbeat.stop()
        if self.sm.get_state() != State.RECONNECTING:
            self.sm.transition(State.RECONNECTING)

    def on_ws_message(self, message):
        # Se for binário, é áudio de TTS para tocar
        if isinstance(message, bytes):
            if self.sm.get_state() == State.WAITING_RESPONSE or self.sm.get_state() == State.PLAYING_TTS:
                if self.sm.get_state() != State.PLAYING_TTS:
                    self.sm.transition(State.PLAYING_TTS)
                self.audio_player.play_chunk(message)
            return

        # Se for texto, parse JSON
        if isinstance(message, str):
            payload = decode_json(message)
            if payload.get("type") == MSG_TYPE_TTS_END:
                # Servidor terminou de enviar o TTS
                # Vamos esperar o watchdog do player encerrar o ffplay
                pass
            
            # Aqui poderíamos implementar START_STREAM, SET_VOLUME, etc, se necessário.
            
    def on_audio_chunk(self, chunk: bytes):
        state = self.sm.get_state()
        
        # ESTADO: LISTENING (Buscando wake word)
        if state == State.LISTENING:
            if self.wake_detector.detect(chunk):
                self.sm.transition(State.WAKE_DETECTED)
                # Opcional: tocar um beep local para avisar que ouviu
                
                self.stream_ctrl.clear()
                self.silence_frames = 0
                self.is_speaking = False
                self.sm.transition(State.STREAMING_AUDIO)
        
        # ESTADO: STREAMING_AUDIO (Ouvindo o comando e enviando)
        elif state == State.STREAMING_AUDIO:
            self.stream_ctrl.add_chunk(chunk, live=False)
            
            is_speech = self.vad.is_speech(chunk)
            
            if is_speech:
                self.is_speaking = True
                self.silence_frames = 0
            else:
                if self.is_speaking:
                    self.silence_frames += 1
            
            # Se detectou silêncio suficiente, corta e envia tudo
            if self.is_speaking and self.silence_frames >= self.max_silence_frames:
                audio_logger.info("Fim da fala detectado.")
                self.stream_ctrl.flush()
                self.sm.transition(State.WAITING_RESPONSE)
        
        # ESTADO: PLAYING_TTS (Terminou de tocar?)
        elif state == State.PLAYING_TTS:
            # O AudioPlayer tem um watchdog que para o ffplay sozinho quando seca o buffer.
            # Se ele secou, voltamos pra LISTENING.
            if self.audio_player.ffplay_proc is None or self.audio_player.ffplay_proc.poll() is not None:
                self.sm.transition(State.LISTENING)
