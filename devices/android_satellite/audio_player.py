import subprocess
import time
import threading
from .logger import player_logger

class AudioPlayer:
    def __init__(self):
        self.ffplay_proc = None
        self.last_byte_time = 0
        self._watchdog_stop = threading.Event()
        self.watchdog_thread = threading.Thread(target=self._watchdog, daemon=True)
        self.watchdog_thread.start()

    def play_chunk(self, audio_bytes: bytes):
        """
        Recebe um chunk binário (ex: WAV/PCM enviado pelo servidor)
        e toca imediatamente via ffplay (pipe).
        """
        self.last_byte_time = time.time()
        
        if self.ffplay_proc is None or self.ffplay_proc.poll() is not None:
            player_logger.info("Iniciando ffplay para reproduzir áudio recebido.")
            try:
                self.ffplay_proc = subprocess.Popen(
                    ['ffplay', '-nodisp', '-autoexit', '-i', 'pipe:0'],
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                player_logger.error(f"Erro ao iniciar ffplay: {e}")
                return

        try:
            self.ffplay_proc.stdin.write(audio_bytes)
            self.ffplay_proc.stdin.flush()
        except Exception as e:
            player_logger.error(f"Erro ao escrever chunk pro ffplay: {e}")
            self.stop()

    def _watchdog(self):
        """
        Encerra graciosamente o ffplay se não recebermos nenhum byte novo
        após um curto período, assumindo que o TTS terminou.
        """
        while not self._watchdog_stop.is_set():
            time.sleep(0.5)
            if self.ffplay_proc is not None and self.ffplay_proc.poll() is None:
                # 1.5s sem novos bytes -> encerra (pode ajustar para menos se quiser corte seco)
                if time.time() - self.last_byte_time > 1.5:
                    player_logger.debug("Fim do fluxo TTS, fechando ffplay...")
                    self.stop()

    def stop(self):
        if self.ffplay_proc:
            try:
                self.ffplay_proc.stdin.close()
                self.ffplay_proc.wait(timeout=1)
            except Exception:
                pass
            finally:
                if self.ffplay_proc.poll() is None:
                    self.ffplay_proc.kill()
                self.ffplay_proc = None

    def __del__(self):
        self._watchdog_stop.set()
        self.stop()
