import logging
from .config import config

def setup_logger():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
def get_logger(name: str):
    return logging.getLogger(name)

# Module specific loggers
state_logger = get_logger("[STATE]")
ws_logger = get_logger("[WS]")
audio_logger = get_logger("[AUDIO]")
vad_logger = get_logger("[VAD]")
wake_logger = get_logger("[WAKE]")
tts_logger = get_logger("[TTS]")
stream_logger = get_logger("[STREAM]")
player_logger = get_logger("[PLAYER]")
