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
        Monitora o processo ffplay. Quando ele terminar naturalmente (autoexit),
        limpa a referência.
        """
        while not self._watchdog_stop.is_set():
            time.sleep(0.5)
            if self.ffplay_proc is not None and self.ffplay_proc.poll() is not None:
                # O ffplay terminou de tocar e saiu sozinho
                self.ffplay_proc = None

    def finish_stream(self):
        """
        Sinaliza ao ffplay que não enviaremos mais bytes (fecha o stdin).
        Com a flag -autoexit, o ffplay vai continuar tocando o buffer até o fim e fechar sozinho.
        """
        if self.ffplay_proc and self.ffplay_proc.poll() is None:
            try:
                self.ffplay_proc.stdin.close()
            except Exception:
                pass

    def stop(self):
        if self.ffplay_proc:
            try:
                self.ffplay_proc.kill()
            except Exception:
                pass
            self.ffplay_proc = None

    def __del__(self):
        self._watchdog_stop.set()
        self.stop()
