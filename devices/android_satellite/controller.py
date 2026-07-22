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

        # Watchdogs de timeout para evitar estados presos
        self._response_start_time = 0.0   # timestamp de quando entrou em WAITING_RESPONSE
        self._playback_start_time = 0.0   # timestamp de quando entrou em PLAYING_TTS
        self.RESPONSE_TIMEOUT = 15.0      # max 15s esperando resposta do servidor
        self.PLAYBACK_TIMEOUT = 30.0      # max 30s de reprodução (ffplay pode travar)

        # Dashcam buffer: mantém os últimos ~2s de áudio PCM16 para incluir
        # a wake word no áudio enviado ao servidor. O servidor precisa
        # encontrar "alexa" no texto transcrito para processar o comando.
        self.dashcam_buffer = bytearray()
        self.dashcam_max_bytes = 2 * config.RATE * 2  # 2s × 16kHz × 2 bytes

        # Cooldown entre gravações: evita que falsos positivos da wake word
        # gerem gravações consecutivas e queimem tokens à toa.
        self._last_recording_time = 0.0
        self.MIN_RECORDING_INTERVAL = 3.0  # 3 segundos mínimo entre gravações

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
                    self._playback_start_time = time.time()
                self.audio_player.play_chunk(message)
            return

        # Se for texto, parse JSON
        if isinstance(message, str):
            payload = decode_json(message)
            if payload.get("type") == MSG_TYPE_TTS_END:
                # Servidor terminou de enviar os bytes de TTS.
                self.audio_player.finish_stream()
                
                # Se não chegou a entrar em PLAYING_TTS (áudio vazio), forçamos a volta:
                if self.sm.get_state() == State.WAITING_RESPONSE:
                    self.sm.transition(State.LISTENING)
                    # Dá um tempo para limpar buffers de microfone
                    self.ignore_wake_until = time.time() + 1.0
            elif payload.get("type") == "START_STREAM":
                ws_logger.info("Iniciando modo transmissão ao vivo (Dashboard)")
                self.sm.transition(State.STREAMING_ONLY)
            elif payload.get("type") == "STOP_STREAM":
                ws_logger.info("Parando transmissão ao vivo (Dashboard)")
                self.sm.transition(State.LISTENING)
                self.ignore_wake_until = time.time() + 1.0
            
    def on_audio_chunk(self, chunk: bytes):
        state = self.sm.get_state()
        
        # ESTADO: STREAMING_ONLY (Enviando áudio contínuo para o dashboard)
        if state == State.STREAMING_ONLY:
            self.stream_ctrl.add_chunk(chunk, live=True)
            return

        # ESTADO: LISTENING (Buscando wake word)
        elif state == State.LISTENING:
            # Alimenta o dashcam buffer continuamente (pré-wake word)
            self.dashcam_buffer.extend(chunk)
            if len(self.dashcam_buffer) > self.dashcam_max_bytes:
                del self.dashcam_buffer[:len(self.dashcam_buffer) - self.dashcam_max_bytes]

            if time.time() < getattr(self, 'ignore_wake_until', 0):
                return
                
            if self.wake_detector.detect(chunk):
                # Cooldown: ignora wake word se gravou recentemente (evita
                # loop de falsos positivos em conversa ambiente).
                now = time.time()
                if now - self._last_recording_time < self.MIN_RECORDING_INTERVAL:
                    return

                self.sm.transition(State.WAKE_DETECTED)
                
                # Prepara o buffer: dashcam (contém a wake word) + gravação nova
                self.stream_ctrl.clear()
                self.stream_ctrl.audio_buffer.extend(self.dashcam_buffer)
                self.dashcam_buffer.clear()
                
                self.silence_frames = 0
                self.is_speaking = False
                self._last_recording_time = now
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
                # Reseta o modelo OWW para evitar re-detecção da mesma
                # wake word no áudio que acabou de ser enviado.
                self.wake_detector.reset()
                self.sm.transition(State.WAITING_RESPONSE)
                self._response_start_time = time.time()
        
        # ESTADO: WAITING_RESPONSE (Aguardando resposta do servidor)
        elif state == State.WAITING_RESPONSE:
            # Watchdog: se o servidor não responder em RESPONSE_TIMEOUT segundos,
            # volta para LISTENING para não travar o satélite para sempre.
            if time.time() - self._response_start_time > self.RESPONSE_TIMEOUT:
                audio_logger.warning(
                    "Timeout de resposta (%ds) — voltando para LISTENING",
                    self.RESPONSE_TIMEOUT,
                )
                self.sm.transition(State.LISTENING)
                self.ignore_wake_until = time.time() + 1.0

        # ESTADO: PLAYING_TTS (Terminou de tocar?)
        elif state == State.PLAYING_TTS:
            # Watchdog: se o ffplay travar (Android pode travar o pipe de áudio),
            # força transição após PLAYBACK_TIMEOUT segundos.
            playback_elapsed = time.time() - self._playback_start_time
            if playback_elapsed > self.PLAYBACK_TIMEOUT:
                audio_logger.warning(
                    "Timeout de reprodução (%ds) — forçando transição para LISTENING",
                    self.PLAYBACK_TIMEOUT,
                )
                self.audio_player.stop()
                self.sm.transition(State.LISTENING)
                self.ignore_wake_until = time.time() + 1.5
            # O AudioPlayer tem um watchdog que para o ffplay sozinho quando seca o buffer.
            # Se ele secou, voltamos pra LISTENING.
            elif self.audio_player.ffplay_proc is None or self.audio_player.ffplay_proc.poll() is not None:
                self.sm.transition(State.LISTENING)
                # Ignora wake word por 1.5s após falar para não ouvir o próprio eco
                self.ignore_wake_until = time.time() + 1.5
