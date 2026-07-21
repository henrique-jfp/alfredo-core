import sys
from .logger import setup_logger, state_logger
from .controller import Controller
from .config import config

def main():
    setup_logger()
    
    state_logger.info("=========================================")
    state_logger.info(" ALFREDO ANDROID SATELLITE (MODULAR)     ")
    state_logger.info("=========================================")
    state_logger.info(f"Dispositivo: {config.DEVICE_ID} | Sala: {config.ROOM_ID}")
    
    controller = Controller()
    
    try:
        controller.start()
    except KeyboardInterrupt:
        state_logger.info("Encerrando satélite...")
        sys.exit(0)
    except Exception as e:
        state_logger.critical(f"Falha crítica no satélite: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
