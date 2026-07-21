import time
import math
from .logger import ws_logger

class ReconnectStrategy:
    def __init__(self, initial_delay=1.0, max_delay=10.0, factor=2.0):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.factor = factor
        self.attempts = 0

    def wait(self):
        if self.attempts == 0:
            delay = self.initial_delay
        else:
            delay = self.initial_delay * math.pow(self.factor, self.attempts)
            
        delay = min(delay, self.max_delay)
        
        ws_logger.info(f"Aguardando {delay:.1f}s antes de reconectar (tentativa {self.attempts + 1})...")
        time.sleep(delay)
        
        self.attempts += 1

    def reset(self):
        self.attempts = 0
