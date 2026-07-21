from dataclasses import dataclass

@dataclass
class AudioChunk:
    data: bytes
    is_speech: bool = False
