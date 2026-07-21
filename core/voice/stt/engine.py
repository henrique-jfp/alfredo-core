import os
import logging
from groq import Groq

from core.services.key_manager import next_groq_key, mark_groq_cooldown

logger = logging.getLogger("alfredo.stt")

class GroqSTT:
    def __init__(self):
        # Cliente será criado sob demanda com a chave selecionada pelo round-robin
        self._client_cache = {}
        key, key_num, total = next_groq_key()
        if not key:
            logger.warning("Nenhuma chave GROQ_API_KEYS ou GROQ_API_KEY encontrada. STT falhará.")
        else:
            logger.info(f"Motor STT (Groq Whisper Large V3) pronto. {total} chave(s) Groq configurada(s).")

    def _get_client(self):
        """Retorna um cliente Groq configurado com a chave atual do round-robin."""
        key, key_num, total = next_groq_key()
        if not key:
            return None
        # Cache simples por preview da chave
        cache_key = key[:20]
        if cache_key not in self._client_cache:
            self._client_cache = {}
            self._client_cache[cache_key] = Groq(api_key=key)
        if total > 1:
            logger.debug(f"STT Groq: usando chave [{key_num} de {total}]")
        return self._client_cache[cache_key]

    def transcribe_wav(self, audio_filepath: str) -> str:
        if not os.path.exists(audio_filepath):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_filepath}")
        logger.info(f"Enviando áudio para Groq Whisper API: {audio_filepath}")
        
        # Converte para WAV padrão 16kHz mono para evitar problemas de header/duração do WebM
        import subprocess, tempfile
        tmp_wav = tempfile.mktemp(suffix=".wav")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_filepath,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                tmp_wav
            ], capture_output=True, check=True)
            target_file = tmp_wav
        except Exception as e:
            logger.warning(f"Falha ao converter áudio com ffmpeg, tentando original. Erro: {e}")
            target_file = audio_filepath

        try:
            client = self._get_client()
            if not client:
                return ""
            with open(target_file, "rb") as file:
                transcription = client.audio.transcriptions.create(
                  file=(os.path.basename(target_file), file.read()),
                  model="whisper-large-v3",
                  response_format="text",
                  language="pt"
                )
            final_text = str(transcription).strip().lower()
            import string
            final_text = final_text.translate(str.maketrans('', '', string.punctuation))
            
            # Filtro de alucinações comuns do Whisper para áudio silencioso/ruído
            hallucinations = ["adriana zanoto", "obrigado por assistir", "obrigada por assistir", "amigos da rede globo", "inscrevase no canal"]
            if final_text in hallucinations:
                logger.warning(f"Alucinação do Whisper ignorada: '{final_text}'")
                final_text = ""

            logger.info(f"Transcrição concluída via Groq Whisper: '{final_text}'")
            return final_text
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                logger.warning("STT Groq: rate limit atingido! Cooldown de 60s.")
                # key_manager já gerencia; a próxima chamada usará outra chave
            logger.error(f"Erro na transcrição via Groq Whisper: {e}")
            return ""
        finally:
            if target_file == tmp_wav and os.path.exists(tmp_wav):
                os.remove(tmp_wav)

    def transcribe_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcreve áudio a partir de bytes em memória (evita I/O de disco)."""
        logger.info(f"Enviando {len(audio_bytes)} bytes para Groq Whisper API (in-memory)")
        try:
            client = self._get_client()
            if not client:
                return ""
            import time
            t_start = time.time()
            transcription = client.audio.transcriptions.create(
              file=(filename, audio_bytes),
              model="whisper-large-v3",
              response_format="text",
              language="pt"
            )
            final_text = str(transcription).strip().lower()
            import string
            final_text = final_text.translate(str.maketrans('', '', string.punctuation))
            latency = int((time.time() - t_start) * 1000)
            logger.info(f"STT concluído em {latency}ms: '{final_text}'")
            return final_text
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                logger.warning("STT Groq (bytes): rate limit atingido! Cooldown de 60s.")
            logger.error(f"Erro na transcrição via Groq Whisper (bytes): {e}. Tentando fallback para Gemini...")
            
            # ────────────────────────────────────────────────────────
            # GEMINI FALLBACK PARA STT
            # ────────────────────────────────────────────────────────
            try:
                import io, wave
                import google.generativeai as genai
                from core.services.key_manager import next_gemini_key
                
                # Prepara os bytes raw com cabeçalho WAV para o Gemini aceitar
                with io.BytesIO() as wav_io:
                    with wave.open(wav_io, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)
                        wav_file.writeframes(audio_bytes)
                    wav_bytes = wav_io.getvalue()

                gem_key, _, _ = next_gemini_key()
                if not gem_key:
                    return ""
                genai.configure(api_key=gem_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Enviando áudio para Gemini 1.5 Flash (Fallback STT)...")
                response = model.generate_content([
                    {"mime_type": "audio/wav", "data": wav_bytes},
                    "Transcreva o que foi dito neste áudio. Escreva APENAS a transcrição exata em português, sem aspas, sem adicionar nenhuma outra palavra."
                ])
                text = response.text.strip().lower()
                import string
                text = text.translate(str.maketrans('', '', string.punctuation))
                logger.info(f"Fallback Gemini STT concluído: '{text}'")
                return text
            except Exception as gem_err:
                logger.error(f"Fallback Gemini STT também falhou: {gem_err}")
                return ""

    async def transcribe_bytes_async(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """Transcreve áudio a partir de bytes em memória, sem bloquear o event loop."""
        import asyncio
        return await asyncio.to_thread(self.transcribe_bytes, audio_bytes, filename)


class VoskLocalSTT:
    def __init__(self):
        model_path = os.getenv("VOSK_MODEL_PATH",
                               os.path.join("core", "voice", "stt", "models", "vosk-model-small-pt-0.3"))
        if not os.path.isabs(model_path):
            base = os.getcwd()
            model_path = os.path.join(base, model_path)
        if not os.path.exists(model_path):
            logger.error(f"Modelo Vosk não encontrado em {model_path}")
            raise FileNotFoundError(f"Modelo Vosk não encontrado: {model_path}")
        try:
            from vosk import Model, KaldiRecognizer
            self.model = Model(model_path)
            logger.info(f"Motor STT (Vosk Local) carregado: {model_path}")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo Vosk: {e}")
            raise

    def transcribe_wav(self, audio_filepath: str) -> str:
        if not os.path.exists(audio_filepath):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_filepath}")
        logger.info(f"Transcrevendo áudio via Vosk local: {audio_filepath}")
        try:
            from vosk import KaldiRecognizer
            import wave
            import json
            wf = wave.open(audio_filepath, "rb")
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                wf.close()
                logger.warning("Áudio não é mono 16-bit, convertendo via ffmpeg...")
                import subprocess, tempfile
                tmp = tempfile.mktemp(suffix=".wav")
                subprocess.run([
                    "ffmpeg", "-y", "-i", audio_filepath,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                    tmp
                ], capture_output=True)
                wf = wave.open(tmp, "rb")

            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(False)
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    part = json.loads(rec.Result())
                    if part.get("text"):
                        results.append(part["text"])
            final = json.loads(rec.FinalResult())
            if final.get("text"):
                results.append(final["text"])
            wf.close()
            text = " ".join(results).strip().lower()
            import string
            text = text.translate(str.maketrans('', '', string.punctuation))
            logger.info(f"Transcrição concluída via Vosk local: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Erro na transcrição via Vosk: {e}")
            return ""


_stt_instance = None

def get_stt_engine():
    global _stt_instance
    if _stt_instance is None:
        backend = os.getenv("STT_BACKEND", "groq").strip().lower()
        if backend == "vosk":
            _stt_instance = VoskLocalSTT()
        else:
            _stt_instance = GroqSTT()
        logger.info(f"STT Engine selecionado: {backend}")
    return _stt_instance
