import os

class Config:
    SERVER_URL = os.getenv("ALFREDO_SERVER_URL", "ws://192.168.0.56:10001")
    DEVICE_ID = os.getenv("ALFREDO_DEVICE_ID", "SAT_BEDROOM")
    ROOM_ID = os.getenv("ALFREDO_ROOM_ID", "bedroom_casal")
    
    # Audio config
    RATE = 16000
    CHANNELS = 1
    DTYPE = 'int16'
    CHUNK = 480  # 480 frames * 2 bytes = 960 bytes (30ms at 16kHz)
    
    # VAD config
    SILENCE_TIMEOUT_MS = 800
    VAD_MODE = 3 # Agressivo
    
    # Wake Word config
    WAKEWORD_MODEL = "alexa" # ou alfredo
    
    # Network config
    PING_INTERVAL = 10
    
    # Log config
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

config = Config()
