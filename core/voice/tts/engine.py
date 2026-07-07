import os
import re
import json
import struct
import logging
import asyncio
import subprocess
import edge_tts


logger = logging.getLogger("alfredo.tts")


# ──────────────────────────────────────────────
# Edge-TTS (backend cloud, fallback padrão)
# ──────────────────────────────────────────────

class TTSEngine:
    def __init__(self, voice_name: str = "pt-BR-FranciscaNeural"):
        self.current_voice_name = voice_name
        self._media_type = "audio/mpeg"
        logger.info(f"Modelo Edge-TTS inicializado com a voz: {voice_name}")

    @property
    def media_type(self) -> str:
        return self._media_type

    def reload_voice(self, voice_name: str):
        if self.current_voice_name != voice_name:
            self.current_voice_name = voice_name
            logger.info(f"Voz Edge-TTS alterada para: {voice_name}")

    async def synthesize_wav(self, text: str, output_filepath: str):
        import uuid, shutil
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        logger.info(f"Sintetizando áudio na nuvem para o texto: '{clean_text}'")

        VOICE_MAP = {
            "en-US": "en-US-AriaNeural", "es-ES": "es-ES-ElviraNeural",
            "de-DE": "de-DE-AmalaNeural", "fr-FR": "fr-FR-DeniseNeural",
            "it-IT": "it-IT-IsabellaNeural", "ja-JP": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural"
        }

        pattern = r'<lang="([^"]+)">(.*?)</lang>'
        parts = re.split(pattern, clean_text)
        parsed_segments = []
        i = 0
        while i < len(parts):
            if parts[i].strip():
                parsed_segments.append((self.current_voice_name, parts[i].strip()))
            i += 1
            if i < len(parts):
                locale = parts[i]
                inside_text = parts[i+1]
                if inside_text.strip():
                    voice = VOICE_MAP.get(locale, self.current_voice_name)
                    parsed_segments.append((voice, inside_text.strip()))
                i += 2

        if not parsed_segments:
            parsed_segments = [(self.current_voice_name, clean_text)]

        temp_dir = os.path.dirname(output_filepath)
        session_id = str(uuid.uuid4())[:8]
        wav_files = []

        try:
            for idx, (voice, segment_text) in enumerate(parsed_segments):
                tmp_mp3 = os.path.join(temp_dir, f"tmp_{session_id}_{idx}.mp3")
                tmp_wav = os.path.join(temp_dir, f"tmp_{session_id}_{idx}.wav")

                communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
                await communicate.save(tmp_mp3)

                cmd = ["ffmpeg", "-y", "-i", tmp_mp3, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp_wav]
                process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.error(f"Erro ffmpeg: {stderr.decode()}")
                    raise Exception("Falha na conversão de áudio para WAV")
                wav_files.append(tmp_wav)
                if os.path.exists(tmp_mp3):
                    os.remove(tmp_mp3)

            if len(wav_files) == 1:
                shutil.move(wav_files[0], output_filepath)
            else:
                concat_cmd = ["ffmpeg", "-y"]
                for w in wav_files:
                    concat_cmd.extend(["-i", w])
                filter_str = "".join([f"[{j}:0]" for j in range(len(wav_files))])
                filter_str += f"concat=n={len(wav_files)}:v=0:a=1[out]"
                concat_cmd.extend(["-filter_complex", filter_str, "-map", "[out]", output_filepath])
                process = await asyncio.create_subprocess_exec(*concat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    logger.error(f"Erro concat ffmpeg: {stderr.decode()}")
                    raise Exception("Falha na concatenação dos áudios")
            logger.info(f"Áudio TTS salvo em: {output_filepath}")
        except Exception as e:
            logger.error(f"Erro na síntese TTS: {e}")
            raise
        finally:
            for w in wav_files:
                if os.path.exists(w):
                    try: os.remove(w)
                    except: pass

    async def stream_audio_generator(self, text: str):
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
        logger.info(f"Iniciando stream TTS para: '{clean_text}'")

        VOICE_MAP = {
            "en-US": "en-US-AriaNeural", "es-ES": "es-ES-ElviraNeural",
            "de-DE": "de-DE-AmalaNeural", "fr-FR": "fr-FR-DeniseNeural",
            "it-IT": "it-IT-IsabellaNeural", "ja-JP": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural"
        }

        pattern = r'<lang="([^"]+)">(.*?)</lang>'
        parts = re.split(pattern, clean_text)
        parsed_segments = []
        i = 0
        while i < len(parts):
            if parts[i].strip():
                parsed_segments.append((self.current_voice_name, parts[i].strip()))
            i += 1
            if i < len(parts):
                locale = parts[i]
                inside_text = parts[i+1]
                if inside_text.strip():
                    voice = VOICE_MAP.get(locale, self.current_voice_name)
                    parsed_segments.append((voice, inside_text.strip()))
                i += 2
        if not parsed_segments:
            parsed_segments = [(self.current_voice_name, clean_text)]

        for voice, segment_text in parsed_segments:
            communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

    async def stream_audio_from_generator(self, text_generator):
        logger.info("Iniciando stream TTS encadeado (LLM -> Edge-TTS)...")

        VOICE_MAP = {
            "en-US": "en-US-AriaNeural", "es-ES": "es-ES-ElviraNeural",
            "de-DE": "de-DE-AmalaNeural", "fr-FR": "fr-FR-DeniseNeural",
            "it-IT": "it-IT-IsabellaNeural", "ja-JP": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural"
        }

        async for sentence in text_generator:
            clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', sentence)
            if not clean_text.strip():
                continue
            pattern = r'<lang="([^"]+)">(.*?)</lang>'
            parts = re.split(pattern, clean_text)
            parsed_segments = []
            i = 0
            while i < len(parts):
                if parts[i].strip():
                    parsed_segments.append((self.current_voice_name, parts[i].strip()))
                i += 1
                if i < len(parts):
                    locale = parts[i]
                    inside_text = parts[i+1]
                    if inside_text.strip():
                        voice = VOICE_MAP.get(locale, self.current_voice_name)
                        parsed_segments.append((voice, inside_text.strip()))
                    i += 2
            if not parsed_segments:
                parsed_segments = [(self.current_voice_name, clean_text)]
            for voice, segment_text in parsed_segments:
                communicate = edge_tts.Communicate(segment_text, voice, rate='+25%')
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]


# ──────────────────────────────────────────────
# Piper TTS (backend local, sem cloud)
# ──────────────────────────────────────────────

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")


def _build_wav_header(sample_rate: int, data_size: int, sample_width: int = 2, channels: int = 1) -> bytes:
    header_size = 44
    total_size = header_size + data_size
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", total_size - 8))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))
    header.extend(struct.pack("<H", 1))
    header.extend(struct.pack("<H", channels))
    header.extend(struct.pack("<I", sample_rate))
    header.extend(struct.pack("<I", sample_rate * sample_width * channels))
    header.extend(struct.pack("<H", sample_width * channels))
    header.extend(struct.pack("<H", sample_width * 8))
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    return bytes(header)


def _find_piper_binary() -> str | None:
    for name in ["piper", "piper.exe", "piper-tts"]:
        try:
            result = subprocess.run(["which", name], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            pass
        # Try where for Windows
        try:
            result = subprocess.run(["where", name], capture_output=True, text=True, timeout=3, shell=True)
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0]
        except:
            pass
    return None


class PiperTTS:
    """Síntese de fala local usando Piper TTS (sem cloud, sem AVX necessário)."""

    def __init__(self, model_path: str | None = None):
        self._media_type = "audio/wav"
        if model_path is None:
            model_path = os.path.join(MODELS_DIR, "pt_BR-faber-medium.onnx")
        self.model_path = model_path
        self._sample_rate: int | None = None

        # Carrega sample rate do JSON do modelo
        json_path = self.model_path + ".json"
        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    cfg = json.load(f)
                self._sample_rate = cfg.get("audio", {}).get("sample_rate", 22050)
            except Exception as e:
                logger.warning(f"Falha ao ler config do modelo Piper: {e}")
                self._sample_rate = 22050
        else:
            self._sample_rate = 22050

        # Verifica se o binário existe
        self._piper_bin = _find_piper_binary()
        if self._piper_bin is None:
            logger.warning(
                "Piper binary não encontrado no PATH. "
                "Instale com: pip install piper-tts && piper --help"
            )

        logger.info(
            f"Piper TTS inicializado: modelo={os.path.basename(model_path)}, "
            f"sample_rate={self._sample_rate}, "
            f"binário={'encontrado' if self._piper_bin else 'NÃO ENCONTRADO'}"
        )

    @property
    def media_type(self) -> str:
        return self._media_type

    def reload_voice(self, voice_name: str):
        """Piper usa apenas o modelo fixo — reload é no-op."""
        pass

    async def _text_to_wav(self, text: str) -> bytes:
        """Executa Piper e retorna WAV completo como bytes."""
        if self._piper_bin is None:
            raise RuntimeError("Piper binary não está instalado. `pip install piper-tts`")

        # Piper lê texto do stdin, escreve raw PCM no stdout
        cmd = [self._piper_bin, "--model", self.model_path, "--output-raw"]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        raw_pcm, stderr = await process.communicate(text.encode("utf-8"))

        if process.returncode != 0:
            err_msg = stderr.decode(errors="replace")[:300]
            raise RuntimeError(f"Piper TTS falhou (código {process.returncode}): {err_msg}")

        if not raw_pcm or len(raw_pcm) < 100:
            raise RuntimeError(f"Piper gerou áudio muito curto ({len(raw_pcm)} bytes)")

        header = _build_wav_header(self._sample_rate, len(raw_pcm))
        return header + raw_pcm

    async def stream_audio_generator(self, text: str):
        """Gera WAV completo a partir de texto único e faz yield em chunks."""
        wav_bytes = await self._text_to_wav(text)
        chunk_size = 4096
        for i in range(0, len(wav_bytes), chunk_size):
            yield wav_bytes[i:i + chunk_size]

    async def stream_audio_from_generator(self, text_generator):
        """
        Recebe AsyncGenerator de frases, gera WAV para cada uma em sequência,
        fazendo yield de chunks. Permite overlap: áudio da frase N toca
        enquanto Piper gera frase N+1.
        """
        logger.info("Iniciando stream TTS encadeado (LLM -> Piper)...")

        async for sentence in text_generator:
            clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', sentence).strip()
            if not clean_text:
                continue

            wav_bytes = await self._text_to_wav(clean_text)
            chunk_size = 4096
            for i in range(0, len(wav_bytes), chunk_size):
                yield wav_bytes[i:i + chunk_size]


# ──────────────────────────────────────────────
# Factory: seleciona backend via env TTS_BACKEND
# ──────────────────────────────────────────────

_tts_instance = None


def get_tts_engine():
    global _tts_instance
    if _tts_instance is None:
        backend = os.getenv("TTS_BACKEND", "edge").strip().lower()
        if backend == "piper":
            logger.info("TTS_BACKEND=piper → usando Piper TTS local (lento neste hardware)")
            _tts_instance = PiperTTS()
        else:
            logger.info("TTS_BACKEND=edge → usando Edge-TTS (cloud)")
            _tts_instance = TTSEngine()
    return _tts_instance
