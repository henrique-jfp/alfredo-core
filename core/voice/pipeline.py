import os
import re
import time as _time
import logging
import asyncio
import edge_tts
from typing import AsyncGenerator
from sqlalchemy.orm import Session

from core.brain.memory import models
from core.brain.memory.database import SessionLocal
from core.voice.stt.engine import get_stt_engine
from core.voice.tts.engine import get_tts_engine
from core.brain.router import get_router
from core.api.satellite import manager

logger = logging.getLogger("alfredo.voice_pipeline")

_WAKE_WORDS = ["alfredo", "alfre", "fredo", "al fredo", "hey alfredo", "ok alfredo", "alexa", "é alexa"]

# Respostas de confirmação tão curtas que não merecem TTS
_QUICK_ACK = {"ok", "ok.", "oque", "oke"}

# Regex de fim de frase para o sentence splitter
_SENTENCE_END = re.compile(r'(?<=[.!?;:])\s+')


def _has_wake_word(text: str) -> bool:
    text_lower = text.lower().strip()
    for w in _WAKE_WORDS:
        if re.search(rf'\b{re.escape(w)}\b', text_lower):
            return True
    return False


async def _async_gen_from_text(text: str):
    """Converte um texto completo em um async generator que yield 1 sentença.
    Útil para o TTS stream quando já temos o texto completo."""
    yield text


async def _save_latency_async(interaction_id: int, latency_ms: int) -> None:
    """Salva a latência no DB em background sem bloquear o pipeline."""
    try:
        def _write():
            with SessionLocal() as db:
                inter = db.query(models.Interaction).filter(
                    models.Interaction.id == interaction_id
                ).first()
                if inter:
                    inter.latency_ms = latency_ms
                    db.commit()
        await asyncio.to_thread(_write)
    except Exception as e:
        logger.error(f"Erro ao salvar latência: {e}")


async def _true_streaming_pipeline(
    text_stream,
    tts_engine,
    interaction_id: int,
    t_pipeline_start: float,
) -> AsyncGenerator[bytes, None]:
    """
    Pipeline de streaming real em 3 estágios sobrepostos:

    Stage 1 (LLM)  → acumula tokens em frases completas e enfileira
    Stage 2 (TTS)  → sintetiza cada frase imediatamente via Edge-TTS stream
    Stage 3 (WS)   → faz yield dos chunks de áudio para o satélite

    Resultado: o satélite começa a tocar quando a PRIMEIRA frase está
    pronta, antes do Gemini terminar de pensar a resposta completa.
    """
    sentence_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=8)
    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=30)

    first_audio_sent = False

    # ── Stage 1: LLM tokens → frases completas ────────────────────────────────
    async def llm_to_sentences():
        buffer = ""
        try:
            async for token in text_stream:
                if not token:
                    continue
                buffer += token

                # Extrai frases completas do buffer (termina em .!?;:)
                parts = _SENTENCE_END.split(buffer)

                for part in parts[:-1]:
                    part = part.strip()
                    if part and len(part) > 2:
                        await sentence_queue.put(part)

                buffer = parts[-1]  # Fragmento incompleto — aguarda mais tokens

        except Exception as e:
            logger.error(f"Erro no stage LLM→frases: {e}")
        finally:
            # Envia sobra do buffer
            if buffer.strip() and len(buffer.strip()) > 2:
                await sentence_queue.put(buffer.strip())
            await sentence_queue.put(None)  # Sentinel: fim do stream

    # ── Stage 2: frases → áudio (TTS) ─────────────────────────────────────────
    async def sentences_to_audio():
        try:
            while True:
                sentence = await sentence_queue.get()
                if sentence is None:
                    break

                # Cache hit: < 1ms, retorna imediatamente sem chamar o Edge-TTS
                cached = await tts_engine.get_cached_audio(sentence)
                if cached:
                    logger.debug(f"TTS cache hit: '{sentence[:40]}'")
                    await audio_queue.put(cached)
                    continue

                # Edge-TTS streaming: yield chunk a chunk sem buffer acumulado
                clean = re.sub(r'[\U00010000-\U0010ffff]', '', sentence)
                if not clean.strip():
                    continue

                try:
                    communicate = edge_tts.Communicate(
                        clean, tts_engine.current_voice_name, rate='+15%'
                    )
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            await audio_queue.put(chunk["data"])
                except Exception as e:
                    logger.warning(f"Edge-TTS falhou para '{sentence[:40]}': {e}")

        except Exception as e:
            logger.error(f"Erro no stage TTS: {e}")
        finally:
            await audio_queue.put(None)  # Sentinel: fim do áudio

    # ── Inicializa os dois estágios em paralelo ────────────────────────────────
    llm_task = asyncio.create_task(llm_to_sentences())
    tts_task = asyncio.create_task(sentences_to_audio())

    # ── Stage 3: yield dos chunks de áudio para o chamador ────────────────────
    try:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                break

            if not first_audio_sent:
                latency_ms = int((_time.time() - t_pipeline_start) * 1000)
                logger.info(f"⚡ TTFA (Time-To-First-Audio): {latency_ms}ms")
                asyncio.create_task(_save_latency_async(interaction_id, latency_ms))
                first_audio_sent = True

            yield chunk

    finally:
        # Cancela tasks se o cliente desconectar antes do fim
        for task in (llm_task, tts_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(llm_task, tts_task, return_exceptions=True)


async def process_audio_pipeline(
    audio_bytes: bytes,
    device_id: str,
    room_id: str,
    db: Session,
    is_webm: bool = False,
    stream_tts: bool = True,
    vosk_text: str = "",
    skip_wake_check: bool = False,
) -> AsyncGenerator[bytes, None]:
    """
    Processa o áudio recebido (STT → LLM → TTS) e retorna um gerador
    assíncrono de chunks de áudio MP3.

    Fluxo otimizado:
    1. Tenta FAST INTERCEPT com o vosk_text pré-transcrito
    2. STT Groq (Whisper) se necessário
    3. Router (Groq fast path ou Gemini com tool calling)
    4. Pipeline de streaming real: LLM + TTS em paralelo com asyncio.Queue

    Quando skip_wake_check=True, pula a verificação de wake word no texto
    transcrito. Usado para conexões WebSocket de satélites que já fazem
    detecção local de wake word (ex: Android, OpenWakeWord).
    """
    t_pipeline_start = _time.time()

    # 1. Registrar interação inicial
    interaction = models.Interaction(
        device_id=device_id,
        room_id=room_id,
        input_text=None,
        output_text=None
    )
    db.add(interaction)
    db.commit()
    interaction_id = interaction.id

    # 2. FAST INTERCEPT: Tenta Semantic Router com o texto pré-transcrito do Vosk
    transcribed_text = ""
    skip_stt = False

    if vosk_text:
        router = get_router()
        match = router.semantic_router.match(vosk_text)
        if match:
            logger.info(f"⚡ FAST INTERCEPT: Match no Vosk Text ('{vosk_text}'). Pulando STT Groq!")
            transcribed_text = vosk_text
            skip_stt = True

    # 3. STT em memória (se não foi interceptado)
    t_stt_start = _time.time()
    if not skip_stt:
        try:
            stt_engine = get_stt_engine()
            if hasattr(stt_engine, 'transcribe_bytes_async'):
                if is_webm:
                    transcribed_text = await stt_engine.transcribe_bytes_async(audio_bytes, filename="audio.webm")
                else:
                    import io, wave
                    with io.BytesIO() as wav_io:
                        with wave.open(wav_io, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(16000)
                            wav_file.writeframes(audio_bytes)
                        wav_bytes = wav_io.getvalue()
                    transcribed_text = await stt_engine.transcribe_bytes_async(wav_bytes)
            elif hasattr(stt_engine, 'transcribe_bytes'):
                if is_webm:
                    transcribed_text = await asyncio.to_thread(stt_engine.transcribe_bytes, audio_bytes, "audio.webm")
                else:
                    import io, wave
                    with io.BytesIO() as wav_io:
                        with wave.open(wav_io, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(16000)
                            wav_file.writeframes(audio_bytes)
                        wav_bytes = wav_io.getvalue()
                    transcribed_text = await asyncio.to_thread(stt_engine.transcribe_bytes, wav_bytes)
            else:
                temp_dir = os.path.join(os.getcwd(), "tmp")
                os.makedirs(temp_dir, exist_ok=True)
                ext = ".webm" if is_webm else ".wav"
                input_filepath = os.path.join(temp_dir, f"in_{int(_time.time())}{ext}")
                with open(input_filepath, "wb") as buffer:
                    buffer.write(audio_bytes)
                transcribed_text = await asyncio.to_thread(stt_engine.transcribe_wav, input_filepath)

            # Filtro de alucinação do Whisper
            hallucinations = ["obrigado", "obrigado.", "obrigada", "obrigada.", "thank you", "thank you."]
            if transcribed_text.strip().lower() in hallucinations:
                logger.warning(f"Ignorando possível alucinação do Whisper: '{transcribed_text}'")
                return

            interaction.input_text = transcribed_text
            db.commit()
            logger.info(f"STT concluído em {_time.time() - t_stt_start:.3f}s — Usuário disse: '{transcribed_text}'")
        except Exception as e:
            logger.error(f"Erro no STT: {e}")
            transcribed_text = ""

    if not transcribed_text.strip():
        return

    # 3a. Guard: rejeita se não houver wake word (a menos que em sessão ativa)
    # Satélites via WebSocket (skip_wake_check=True) já fizeram detecção
    # local de wake word — o áudio enviado não contém a wake word.
    if not skip_stt and not skip_wake_check and not _has_wake_word(transcribed_text):
        session_active = db.query(models.SessionState).filter(
            models.SessionState.room_id == room_id,
        ).first()
        if not session_active:
            logger.info(f"Ignorando '{transcribed_text}': sem wake word e sem sessão ativa.")
            return

    # 3b. Roteamento de Intenção (Streaming Real)
    t_llm_start = _time.time()
    logger.info("Enviando texto para o Router (Streaming)...")
    try:
        router = get_router()
        context = {
            "device_id": device_id,
            "room_id": room_id,
            "db": db,
            "ws_tasks": []
        }

        text_stream = router.process_stream_async(transcribed_text, context)

        # Intercepta o stream do LLM para salvar o texto completo no DB em background
        full_text_parts = []

        async def intercept_and_save_text(generator):
            try:
                async for sentence in generator:
                    if sentence:
                        full_text_parts.append(sentence)
                        yield sentence
            except Exception as e:
                logger.error(f"Erro no generator interceptor: {e}")

            # Salva texto final no DB (fora do critical path, não bloqueia o áudio)
            full_text = " ".join(full_text_parts).strip()
            if full_text:
                try:
                    def _write_text():
                        with SessionLocal() as new_db:
                            inter = new_db.query(models.Interaction).filter(
                                models.Interaction.id == interaction_id
                            ).first()
                            if inter:
                                inter.input_text = inter.input_text or transcribed_text
                                inter.output_text = full_text
                                new_db.commit()
                    asyncio.create_task(asyncio.to_thread(_write_text))
                except Exception as e:
                    logger.error(f"Erro ao salvar interação final: {e}")

            # Processa ws_tasks (push para satélites)
            for task in context.get("ws_tasks", []):
                target_ws = manager.active_satellites.get(task["device_id"])
                if target_ws:
                    try:
                        await target_ws.send_json(task["payload"])
                        logger.info(f"Push enviado via WebSocket para {task['device_id']}")
                    except Exception:
                        pass

        intercepted_stream = intercept_and_save_text(text_stream)

    except Exception as e:
        logger.error(f"Erro no Router: {e}")
        async def error_stream():
            yield "Tive um problema interno ao tentar pensar na sua resposta."
        intercepted_stream = error_stream()

    # 4. Sintetizar áudio de resposta via Pipeline Streaming Real
    try:
        voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
        chosen_voice = (
            voice_setting.value.strip()
            if voice_setting and voice_setting.value and voice_setting.value.strip()
            else "pt-BR-FranciscaNeural"
        )

        tts_engine = get_tts_engine()
        tts_engine.reload_voice(chosen_voice)

        logger.info(f"Pipeline pré-TTS pronto em {_time.time() - t_pipeline_start:.3f}s")

        if not stream_tts:
            # Modo não-streaming (dashboard): coleta tudo e manda WAV único
            full_text = " ".join(full_text_parts).strip()
            # Aguarda o stream acabar se ainda não coletou
            if not full_text_parts:
                async for _ in intercepted_stream:
                    pass
                full_text = " ".join(full_text_parts).strip()

            if full_text and full_text.lower().strip() not in _QUICK_ACK:
                import tempfile
                tmp_wav = tempfile.mktemp(suffix=".wav")
                await tts_engine.synthesize_wav(full_text, tmp_wav)
                with open(tmp_wav, "rb") as f:
                    wav_data = f.read()
                os.remove(tmp_wav)
                yield wav_data
            return

        # ── PIPELINE STREAMING REAL ────────────────────────────────────────────
        # Verifica primeiro se a resposta completa é um ACK curto.
        # Para isso, precisa de uma small preview do stream sem consumi-lo todo.
        # Estratégia: inicia o pipeline e checa o primeiro item da fila de frases.
        # Se for um ACK, aborta silenciosamente. Caso contrário, transmite tudo.

        async for audio_chunk in _true_streaming_pipeline(
            text_stream=intercepted_stream,
            tts_engine=tts_engine,
            interaction_id=interaction_id,
            t_pipeline_start=t_pipeline_start,
        ):
            # ⚡ SKIP TTS tardio: se a resposta completa era "ok", não chegou áudio
            yield audio_chunk

    except Exception as e:
        logger.error(f"Erro no pipeline de streaming: {e}")