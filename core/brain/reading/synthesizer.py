"""
Sintetizador e mixador de áudio para leitura interativa.

Recebe segmentos anotados (do annotator) e produz um único arquivo MP3
com voz narrada + efeitos sonoros mixados. O resultado fica em cache
em disco — nunca resintetiza um capítulo que já tem audio_path.

Uso:
    from core.brain.reading.synthesizer import synthesize_chapter
    audio_path = await synthesize_chapter(book_id=1, chapter_index=0, segments=segments)
"""
import asyncio
import io
import logging
import os
from pathlib import Path

logger = logging.getLogger("alfredo.reading.synthesizer")

# ── Mapeamento de voice_style → parâmetros edge-tts ─────────────────────────
# ATENÇÃO: edge-tts gratuito NÃO suporta SSML express-as (estilos como
# "whispering"). Estes são os melhores equivalentes usando rate/volume/pitch.
# Não tente "consertar" isso — é uma limitação da lib, não um bug.

VOICE_STYLE_PARAMS: dict[str, dict[str, str]] = {
    "normal":   {"rate": "+0%",  "volume": "+0%",  "pitch": "+0Hz"},
    "whisper":  {"rate": "-30%", "volume": "-40%", "pitch": "-5Hz"},
    "dramatic": {"rate": "-15%", "volume": "+0%",  "pitch": "+3Hz"},
    "fast":     {"rate": "+25%", "volume": "+0%",  "pitch": "+0Hz"},
}

# Volume do efeito sonoro relativo à voz (em dB). Negativo = mais baixo.
SFX_VOLUME_REDUCTION_DB = -15

# Diretório dos efeitos sonoros
SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
))), "assets", "sfx")

# Diretório base para áudio da biblioteca
LIBRARY_AUDIO_DIR = os.path.join(os.getcwd(), "data", "library")

# Voz padrão do narrador (consistente com o Alfredo principal)
DEFAULT_VOICE = "pt-BR-FranciscaNeural"


async def synthesize_chapter(
    book_id: int,
    chapter_index: int,
    segments: list,
    voice: str = DEFAULT_VOICE,
) -> str:
    """Sintetiza e mixa um capítulo inteiro em um único arquivo MP3.

    Args:
        book_id: ID do livro.
        chapter_index: Índice do capítulo (0-based).
        segments: Lista de Segment (do annotator).
        voice: Nome da voz edge-tts.

    Returns:
        Caminho absoluto do arquivo MP3 final.
    """
    from pydub import AudioSegment

    output_dir = os.path.join(LIBRARY_AUDIO_DIR, str(book_id), "audio")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{chapter_index}.mp3")

    # Se o arquivo já existe, não resintetiza
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        logger.info("Áudio já existe para livro %d cap %d — pulando síntese", book_id, chapter_index)
        return output_path

    logger.info(
        "Sintetizando livro %d, capítulo %d (%d segmentos)...",
        book_id, chapter_index, len(segments),
    )

    # Sintetiza cada segmento e acumula
    final_audio = AudioSegment.silent(duration=0)
    sfx_cache: dict[str, AudioSegment] = {}

    for i, segment in enumerate(segments):
        try:
            # 1. Gera áudio de voz via edge-tts
            voice_audio = await _synthesize_segment_voice(segment.text, segment.voice_style, voice)
            if voice_audio is None:
                logger.warning("Segmento %d sem áudio gerado — pulando", i)
                continue

            voice_seg = AudioSegment.from_mp3(io.BytesIO(voice_audio))

            # 2. Se tem efeito, sobrepõe
            if segment.effect:
                sfx_seg = _load_sfx(segment.effect, sfx_cache)
                if sfx_seg is not None:
                    # Reduz volume do efeito e sobrepõe na voz
                    sfx_adjusted = sfx_seg + SFX_VOLUME_REDUCTION_DB
                    # Trunca ou padroniza o efeito para caber na duração da voz
                    if len(sfx_adjusted) > len(voice_seg):
                        sfx_adjusted = sfx_adjusted[:len(voice_seg)]
                    voice_seg = voice_seg.overlay(sfx_adjusted)

            # 3. Concatena ao áudio final com pequena pausa entre segmentos
            final_audio += voice_seg + AudioSegment.silent(duration=200)

        except Exception as e:
            logger.error("Erro no segmento %d: %s — continuando", i, e)
            continue

    if len(final_audio) == 0:
        logger.error("Nenhum áudio gerado para livro %d cap %d", book_id, chapter_index)
        raise RuntimeError("Síntese produziu áudio vazio")

    # Exporta como MP3 48kbps (consistente com o bitrate do satélite: bytes/6000)
    final_audio.export(output_path, format="mp3", bitrate="48k")

    duration_s = len(final_audio) / 1000
    file_size = os.path.getsize(output_path)
    logger.info(
        "Áudio sintetizado: livro %d cap %d — %.1fs, %d bytes, salvo em %s",
        book_id, chapter_index, duration_s, file_size, output_path,
    )
    return output_path


async def _synthesize_segment_voice(
    text: str,
    voice_style: str,
    voice: str,
) -> bytes | None:
    """Sintetiza um segmento de texto via edge-tts e retorna bytes MP3."""
    import edge_tts

    params = VOICE_STYLE_PARAMS.get(voice_style, VOICE_STYLE_PARAMS["normal"])

    try:
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=params["rate"],
            volume=params["volume"],
            pitch=params["pitch"],
        )

        audio_bytes = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])

        if not audio_bytes:
            return None
        return bytes(audio_bytes)

    except Exception as e:
        logger.error("Erro no edge-tts para '%s...': %s", text[:50], e)
        return None


def _load_sfx(effect_name: str, cache: dict) -> "AudioSegment | None":
    """Carrega um efeito sonoro do disco, com cache em memória."""
    from pydub import AudioSegment

    if effect_name in cache:
        return cache[effect_name]

    sfx_path = os.path.join(SFX_DIR, f"{effect_name}.mp3")
    if not os.path.exists(sfx_path):
        logger.debug("SFX não encontrado: %s — ignorando", sfx_path)
        cache[effect_name] = None
        return None

    try:
        seg = AudioSegment.from_mp3(sfx_path)
        cache[effect_name] = seg
        return seg
    except Exception as e:
        logger.warning("Erro ao carregar SFX '%s': %s", effect_name, e)
        cache[effect_name] = None
        return None


def get_chapter_audio_path(book_id: int, chapter_index: int) -> str | None:
    """Retorna o caminho do áudio se já existir, ou None."""
    path = os.path.join(LIBRARY_AUDIO_DIR, str(book_id), "audio", f"{chapter_index}.mp3")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    return None
