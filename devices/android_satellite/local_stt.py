"""
local_stt.py — Reconhecimento de fala local via Vosk para o satélite Android.

Usa o modelo small de português do Vosk (~31MB, ~300MB RAM em runtime).
Ideal para dispositivos móveis com RAM limitada (Samsung M21: 3.5GB).

Se o modelo full (vosk-model-pt-fb) estiver disponível, é usado como
fallback para maior precisão (mas consome mais RAM).

Modelo small: vosk-model-small-pt-0.3 (31MB)
Download: https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip

Modelo full (fallback): vosk-model-pt-fb-v0.1.1-20220516_2113 (1.6GB)
"""

import json
import logging
import os
import shutil
import tempfile
import zipfile

logger = logging.getLogger("alfredo.satellite.local_stt")


class VoskSTT:
    """
    Wrapper para o Vosk que transcreve chunks de áudio PCM16 16kHz mono.
    Fornece transcrição parcial (streaming) em tempo real.
    """

    def __init__(self, model_path: str | None = None):
        self.model = None
        self.rec = None
        self._loaded = False

        if model_path is None:
            model_path = self._default_model_path()

        if not os.path.exists(model_path):
            logger.warning(
                "Modelo Vosk não encontrado em '%s'. "
                "Comandos offline (TV/luz) NÃO funcionarão neste boot. "
                "Baixe o modelo small em: "
                "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip "
                "ou execute: python3 -c "
                "\"from devices.android_satellite.local_stt import VoskSTT; "
                "VoskSTT.auto_download()\"",
                model_path,
            )
            return

        try:
            import vosk
            vosk.SetLogLevel(-1)  # silencia logs verbosos do Vosk
            self.model = vosk.Model(model_path)
            logger.info(
                "Modelo Vosk carregado: %s (%s)",
                model_path,
                self._human_size(model_path),
            )
            self._loaded = True
        except ImportError:
            logger.error(
                "Vosk não instalado. Execute: pip install vosk"
            )
        except Exception as e:
            logger.error("Erro ao carregar modelo Vosk: %s", e)

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self.model is not None

    def new_recognizer(self, sample_rate: int = 16000):
        """
        Cria um novo KaldiRecognizer para uma nova sessão de transcrição.
        Deve ser chamado antes de cada comando de voz.
        """
        if not self.is_loaded:
            return
        import vosk
        self.rec = vosk.KaldiRecognizer(self.model, sample_rate)
        self.rec.SetWords(False)

    def reset(self):
        """Descarta o recognizer atual."""
        self.rec = None

    def process_chunk(self, audio_bytes: bytes) -> str | None:
        """
        Processa um chunk de áudio PCM16 16kHz mono.

        Retorna:
          - None se não houver transcrição parcial
          - str com o texto parcial reconhecido até agora
          - Se AcceptWaveform retornar True, texto final da frase
        """
        if not self.is_loaded or self.rec is None:
            return None

        try:
            if self.rec.AcceptWaveform(audio_bytes):
                result = json.loads(self.rec.Result())
                text = result.get("text", "").strip()
                if text:
                    return text  # Texto final
            else:
                partial = json.loads(self.rec.PartialResult())
                text = partial.get("partial", "").strip()
                if text:
                    return text  # Texto parcial
        except Exception as e:
            logger.debug("Erro no Vosk process_chunk: %s", e)

        return None

    def final_result(self) -> str:
        """
        Retorna o resultado final forçado (última frase não dita).
        """
        if not self.is_loaded or self.rec is None:
            return ""
        try:
            result = json.loads(self.rec.FinalResult())
            return result.get("text", "").strip()
        except Exception:
            return ""

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _default_model_path() -> str:
        """
        Caminho padrão para o modelo Vosk no Termux/Android.
        Tenta o modelo small primeiro (ideal para mobile), depois full.
        """
        MODELS_TO_TRY = [
            "vosk-model-small-pt-0.3",       # ~31MB, ~300MB RAM
            "vosk-model-pt-fb-v0.1.1-20220516_2113",  # ~1.6GB, ~2GB+ RAM
        ]
        base_dirs = [
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "core", "voice", "stt", "models",
            ),
            os.path.join(
                os.path.expanduser("~"),
                "alfredo-core", "core", "voice", "stt", "models",
            ),
            os.path.expanduser("~"),
        ]
        for model_name in MODELS_TO_TRY:
            for base in base_dirs:
                path = os.path.join(base, model_name)
                if os.path.exists(path):
                    return path
        # Fallback: retorna o primeiro candidate do small model
        return os.path.join(base_dirs[0], MODELS_TO_TRY[0])

    @staticmethod
    def _human_size(path: str) -> str:
        """Retorna o tamanho do diretório de forma legível."""
        try:
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except OSError:
                        pass
            for unit in ("B", "KB", "MB", "GB"):
                if total < 1024:
                    return f"{total:.1f}{unit}"
                total /= 1024
            return f"{total:.1f}TB"
        except Exception:
            return "?"

    @staticmethod
    def auto_download(target_dir: str | None = None, model_name: str | None = None) -> str | None:
        """
        Faz o download automático do modelo Vosk small (pt, ~31MB)
        e extrai no diretório alvo.

        Args:
            target_dir: diretório onde extrair (default: core/voice/stt/models)
            model_name: nome do modelo (default: vosk-model-small-pt-0.3)

        Retorna o caminho do modelo ou None em caso de falha.
        """
        import urllib.request

        if model_name is None:
            model_name = "vosk-model-small-pt-0.3"
        url = (
            "https://alphacephei.com/vosk/models/"
            f"{model_name}.zip"
        )

        if target_dir is None:
            target_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "core", "voice", "stt", "models",
            )

        os.makedirs(target_dir, exist_ok=True)
        zip_path = os.path.join(target_dir, f"{model_name}.zip")
        extract_dir = os.path.join(target_dir, model_name)

        if os.path.exists(extract_dir):
            logger.info("Modelo Vosk já existe em %s", extract_dir)
            return extract_dir

        logger.info("Baixando modelo Vosk (%s)... Aguarde (~31MB)", url)
        try:
            urllib.request.urlretrieve(url, zip_path)
            logger.info("Download concluído. Extraindo...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_dir)
            os.remove(zip_path)
            logger.info("Modelo Vosk extraído em %s", extract_dir)
            return extract_dir
        except Exception as e:
            logger.error("Falha ao baixar/extrair modelo Vosk: %s", e)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return None
