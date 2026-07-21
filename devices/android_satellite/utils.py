import array
import math

def get_rms(data: bytes) -> float:
    """Calcula RMS (Root Mean Square) do áudio PCM16."""
    samples = array.array("h", data[: len(data) - (len(data) % 2)])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))
