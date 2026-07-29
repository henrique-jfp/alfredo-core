"""
AmbienceManager — Mixagem de sons ambientes com TTS em tempo real.

Gera sons ambientes sintéticos (chuva, floresta, café, fogo) usando
numpy/scipy. Mantém loops em PCM na memória e mixa com o áudio TTS
antes de enviar para o satélite, sem exigir processamento no lado
do satélite.

Uso:
    from core.voice.ambience import get_ambience_manager

    ambience = get_ambience_manager()
    ambience.set_ambient("rain")
    # ... processa TTS normalmente ...
    ambience.stop_ambient()
"""

import os
import io
import struct
import logging
import asyncio
import numpy as np
from scipy import signal
from typing import Optional

logger = logging.getLogger("alfredo.ambience")

SAMPLE_RATE = 16000          # Hz (compatível com o TTS Edge → ffmpeg)
AMBIENT_VOLUME = 0.25        # 25% do volume do TTS (não abafa a voz)
LOOP_DURATION = 120          # segundos por loop (cobre qualquer resposta TTS)

# ---------------------------------------------------------------------------
# Geradores de som ambiente sintético (CC0 — código gerado, sem direitos)
# ---------------------------------------------------------------------------

def _pink_noise(n_samples: int) -> np.ndarray:
    """Ruído rosa (1/f) via soma de fontes octave-spaced (algoritmo Voss-McCartney)."""
    # Método simplificado: filtra ruído branco com resposta 1/f
    white = np.random.randn(n_samples + 1).astype(np.float64)
    # Filtro IIR de aproximação 1/f (pink)
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    pink = signal.lfilter(b, a, white)
    return pink[:n_samples]

def _brown_noise(n_samples: int) -> np.ndarray:
    """Ruído marrom (1/f²) — integração cumulativa de ruído branco."""
    white = np.random.randn(n_samples).astype(np.float64)
    brown = np.cumsum(white)
    # Normaliza para evitar overflow
    brown = brown / (np.std(brown) + 1e-10) * 0.3
    return brown

def _generate_rain(n_samples: int) -> np.ndarray:
    """Chuva suave: ruído rosa filtrado (passa-baixa ~2kHz) + ruído de fundo."""
    pink = _pink_noise(n_samples)
    # Filtro passa-baixa para simular som de chuva (atenua agudos)
    sos = signal.butter(4, 2000, 'lp', fs=SAMPLE_RATE, output='sos')
    rain = signal.sosfilt(sos, pink)
    # Adiciona modulação lenta para variar intensidade
    mod = 0.7 + 0.3 * np.sin(2 * np.pi * 0.1 * np.arange(n_samples) / SAMPLE_RATE)
    rain = rain * mod
    # Normaliza
    peak = np.max(np.abs(rain))
    if peak > 0:
        rain = rain / peak * 0.4
    return rain.astype(np.float64)

def _generate_forest(n_samples: int) -> np.ndarray:
    """Floresta: ruído rosa + pássaros (tons senoidais aleatórios) + vento."""
    pink = _pink_noise(n_samples)
    # Vento suave: modulação lenta do ruído
    wind_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * np.arange(n_samples) / SAMPLE_RATE)
    wind = pink * wind_mod * 0.3
    # Pássaros: chirps senoidais curtos e esparsos
    t = np.arange(n_samples)
    birds = np.zeros(n_samples, dtype=np.float64)
    rng = np.random.RandomState(42)
    n_birds = int(n_samples / SAMPLE_RATE * 0.5)  # 0.5 chirp por segundo
    for _ in range(n_birds):
        pos = rng.randint(0, n_samples - SAMPLE_RATE // 2)
        freq = rng.uniform(2000, 5000)
        dur = rng.randint(int(SAMPLE_RATE * 0.05), int(SAMPLE_RATE * 0.15))
        if pos + dur > n_samples:
            continue
        env = np.hanning(dur * 2 + 1)[dur:] if dur > 0 else np.ones(1)
        env = env[:min(len(env), dur)]
        if len(env) < dur:
            env = np.ones(dur)
        chirp = np.sin(2 * np.pi * freq * np.arange(dur) / SAMPLE_RATE) * env * 0.15
        end = min(pos + dur, n_samples)
        birds[pos:end] += chirp[:end - pos]
    forest = wind + birds
    peak = np.max(np.abs(forest))
    if peak > 0:
        forest = forest / peak * 0.35
    return forest.astype(np.float64)

def _generate_cafe(n_samples: int) -> np.ndarray:
    """Café: ruído marrom (vozes ao fundo) + ruído de máquina (chiado suave)."""
    brown = _brown_noise(n_samples)
    # Vozes ao fundo: ruído modulado na faixa de fala (200-2000Hz)
    sos = signal.butter(4, [200, 2000], 'bp', fs=SAMPLE_RATE, output='sos')
    chatter = signal.sosfilt(sos, np.random.randn(n_samples).astype(np.float64))
    chatter = chatter * 0.15
    # Máquina de café: chiado de alta frequência
    hiss = np.random.randn(n_samples).astype(np.float64) * 0.05
    sos_hiss = signal.butter(4, 4000, 'hp', fs=SAMPLE_RATE, output='sos')
    hiss = signal.sosfilt(sos_hiss, hiss)
    cafe = brown * 0.3 + chatter + hiss
    peak = np.max(np.abs(cafe))
    if peak > 0:
        cafe = cafe / peak * 0.3
    return cafe.astype(np.float64)

def _generate_fire(n_samples: int) -> np.ndarray:
    """Fogo/lareira: ruído marrom + estalos aleatórios."""
    brown = _brown_noise(n_samples) * 0.4
    # Estalos: impulsos curtos e esparsos
    t = np.arange(n_samples)
    crackles = np.zeros(n_samples, dtype=np.float64)
    rng = np.random.RandomState(42)
    n_crackles = int(n_samples / SAMPLE_RATE * 1.5)  # 1.5 estalo por segundo
    for _ in range(n_crackles):
        pos = rng.randint(0, n_samples - 1)
        dur = rng.randint(int(SAMPLE_RATE * 0.005), int(SAMPLE_RATE * 0.05))
        if pos + dur > n_samples:
            continue
        env = np.exp(-4 * np.arange(dur) / dur)  # Decaimento rápido
        pop = (np.random.randn(dur) * 0.5 + 0.5) * env * rng.uniform(0.3, 1.0)
        end = min(pos + dur, n_samples)
        crackles[pos:end] += pop[:end - pos]
    fire = brown + crackles * 0.3
    peak = np.max(np.abs(fire))
    if peak > 0:
        fire = fire / peak * 0.35
    return fire.astype(np.float64)


# ---------------------------------------------------------------------------
# Gerenciador de ambientes
# ---------------------------------------------------------------------------

_ambience_instance = None


def get_ambience_manager():
    """Retorna a instância singleton do AmbienceManager."""
    global _ambience_instance
    if _ambience_instance is None:
        _ambience_instance = AmbienceManager()
    return _ambience_instance


class AmbienceManager:
    """
    Gerencia sons ambientes e mixagem com TTS.

    Mantém loops PCM em memória (int16, 16000Hz, mono) e posição atual
    para garantir continuidade. A mixagem decodifica MP3 → PCM, soma
    com o ambiente (volume controlado), e recodifica para MP3.
    """

    def __init__(self):
        self._ambient_type: Optional[str] = None
        self._ambient_pcm: dict[str, tuple[np.ndarray, int]] = {}
        self._position: int = 0          # amostra atual no loop
        self._volume: float = AMBIENT_VOLUME
        self._generated: set[str] = set()

    def _ensure_generated(self, name: str):
        """Gera o som ambiente sob demanda (lazy), apenas quando ativado."""
        if name in self._generated:
            return
        logger.info("Gerando som ambiente: %s...", name)
        n = SAMPLE_RATE * LOOP_DURATION
        generator = {
            "rain":   lambda n=n: self._to_int16(_generate_rain(n)),
            "forest": lambda n=n: self._to_int16(_generate_forest(n)),
            "cafe":   lambda n=n: self._to_int16(_generate_cafe(n)),
            "fire":   lambda n=n: self._to_int16(_generate_fire(n)),
        }
        fn = generator.get(name)
        if fn:
            pcm = fn()
            self._ambient_pcm[name] = (pcm, SAMPLE_RATE)
            self._generated.add(name)
            logger.info("Ambiente '%s' gerado (%d amostras)", name, len(pcm))
        else:
            logger.warning("Ambiente desconhecido: %s", name)

    @staticmethod
    def _to_int16(arr: np.ndarray) -> np.ndarray:
        """Converte float64 [-1, 1] para int16."""
        arr = np.clip(arr, -1.0, 1.0)
        return (arr * 32767).astype(np.int16)

    # ── API pública ──────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._ambient_type is not None

    @property
    def ambient_type(self) -> Optional[str]:
        return self._ambient_type

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, v: float):
        self._volume = max(0.0, min(1.0, v))

    def set_ambient(self, name: str) -> bool:
        """Ativa um ambiente. Retorna True se o nome é válido."""
        name = name.strip().lower()
        if name not in ("rain", "forest", "cafe", "fire"):
            logger.warning("Ambiente desconhecido: '%s'. Opções: rain, forest, cafe, fire", name)
            return False
        # Geração lazy: só gera quando ativado pela primeira vez
        self._ensure_generated(name)
        self._ambient_type = name
        self._position = 0
        logger.info("🌧️  Ambiente ativado: %s (volume=%.0f%%)", name, self._volume * 100)
        return True

    def stop_ambient(self):
        """Desativa o ambiente atual."""
        if self._ambient_type:
            logger.info("🔇 Ambiente desativado: %s", self._ambient_type)
            self._ambient_type = None
            self._position = 0

    def list_ambients(self) -> list[str]:
        """Retorna lista de nomes de ambientes disponíveis."""
        return ["rain", "forest", "cafe", "fire"]

    # ── Mixagem ──────────────────────────────────────────────────────────

    def _get_ambient_segment(self, n_samples: int) -> np.ndarray:
        """Retorna um segmento do loop ambiente a partir da posição atual."""
        if not self._ambient_type:
            return np.zeros(n_samples, dtype=np.int16)
        pcm, rate = self._ambient_pcm[self._ambient_type]
        total = len(pcm)
        if total == 0:
            return np.zeros(n_samples, dtype=np.int16)
        # Calcula segmento com wrapping (loop infinito)
        start = self._position % total
        end = start + n_samples
        if end <= total:
            return pcm[start:end]
        else:
            # Precisa dar a volta
            first = pcm[start:]
            second = pcm[:end - total]
            return np.concatenate([first, second])

    def _advance_position(self, n_samples: int):
        """Avança a posição no loop."""
        self._position = (self._position + n_samples) % (SAMPLE_RATE * LOOP_DURATION)

    async def mix_mp3_batch(self, mp3_chunks: list[bytes]) -> list[bytes]:
        """
        Recebe chunks MP3 do TTS, mixa com o ambiente ativo e retorna
        chunks MP3 mixados. Se não houver ambiente ativo, retorna os
        chunks originais inalterados.

        Usa ffmpeg para decode/encode (ffmpeg está instalado no servidor).
        """
        if not self.is_active or not mp3_chunks:
            return mp3_chunks

        combined = b"".join(mp3_chunks)
        if not combined:
            return mp3_chunks

        # 1. Decodifica MP3 → PCM (s16le, mono, 16kHz)
        tts_pcm = await self._mp3_to_pcm(combined)
        if tts_pcm is None or len(tts_pcm) < 4:
            logger.warning("Falha ao decodificar MP3 para mixagem — enviando original")
            return mp3_chunks

        # 2. Converte para numpy
        tts_arr = np.frombuffer(tts_pcm, dtype=np.int16).astype(np.float64)
        n_tts = len(tts_arr)

        # 3. Pega segmento do ambiente
        ambient_arr = self._get_ambient_segment(n_tts).astype(np.float64)
        self._advance_position(n_tts)

        # 4. Mixa (TTS + ambiente * volume)
        mixed = tts_arr + ambient_arr * self._volume * 32767

        # 5. Satura para int16
        mixed = np.clip(mixed, -32768, 32767).astype(np.int16)

        # 6. Recodifica PCM → MP3
        mixed_mp3 = await self._pcm_to_mp3(mixed.tobytes())
        if mixed_mp3 is None:
            logger.warning("Falha ao recodificar MP3 mixado — enviando original")
            return mp3_chunks

        logger.debug("Mixagem concluída: %d bytes TTS + ambiente '%s' -> %d bytes MP3",
                     len(combined), self._ambient_type, len(mixed_mp3))
        return [mixed_mp3]

    async def _mp3_to_pcm(self, mp3_data: bytes) -> Optional[bytes]:
        """Decodifica MP3 → PCM s16le via ffmpeg."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-i", "pipe:0",
                "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE),
                "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(mp3_data), timeout=30.0
            )
            if proc.returncode != 0:
                err = stderr.decode(errors="replace")[:200]
                logger.error("ffmpeg MP3→PCM falhou (código %d): %s", proc.returncode, err)
                return None
            return stdout
        except asyncio.TimeoutError:
            logger.error("ffmpeg MP3→PCM timeout após 30s")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg não encontrado no PATH")
            return None
        except Exception as e:
            logger.error("Erro ffmpeg MP3→PCM: %s", e)
            return None

    async def _pcm_to_mp3(self, pcm_data: bytes) -> Optional[bytes]:
        """Codifica PCM s16le → MP3 via ffmpeg."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-y",
                "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE),
                "-i", "pipe:0",
                "-f", "mp3", "-b:a", "48k",
                "pipe:1",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(pcm_data), timeout=30.0
            )
            if proc.returncode != 0:
                err = stderr.decode(errors="replace")[:200]
                logger.error("ffmpeg PCM→MP3 falhou (código %d): %s", proc.returncode, err)
                return None
            return stdout
        except asyncio.TimeoutError:
            logger.error("ffmpeg PCM→MP3 timeout após 30s")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg não encontrado no PATH")
            return None
        except Exception as e:
            logger.error("Erro ffmpeg PCM→MP3: %s", e)
            return None
