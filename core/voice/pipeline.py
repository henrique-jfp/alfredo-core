import os
import re
import time as _time
import logging
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

def _has_wake_word(text: str) -> bool:
    text_lower = text.lower().strip()
    for w in _WAKE_WORDS:
        if re.search(rf'\b{re.escape(w)}\b', text_lower):
            return True
    return False

async def process_audio_pipeline(audio_bytes: bytes, device_id: str, room_id: str, db: Session, is_webm: bool = False, stream_tts: bool = True, vosk_text: str = "") -> AsyncGenerator[bytes, None]:
    """
    Processa o áudio recebido (STT -> LLM -> TTS) e retorna um gerador assíncrono de áudio (TTS chunks).
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
    
    # 2. FAST INTERCEPT: Tenta Semantic Router com o texto pré-transcrito do Vosk (satélite)
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
                import asyncio
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
                import asyncio
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

    # 3a. Guarda: rejeita se não houver wake word (a menos que em sessão ativa)
    # O fast path (semantic router com vosk_text) executa antes deste guarda,
    # então comandos determinísticos como "pausa a música" passam mesmo sem wake word.
    if not _has_wake_word(transcribed_text):
        session_active = db.query(models.SessionState).filter(
            models.SessionState.room_id == room_id,
            models.SessionState.is_active == True
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
        
        async def intercept_and_save_text(generator):
            full_text = ""
            try:
                async for sentence in generator:
                    if sentence:
                        full_text += sentence + " "
                        yield sentence
            except Exception as e:
                logger.error(f"Erro no generator: {e}")
                
            # Salvar no DB o texto final usando uma NOVA sessão
            try:
                with SessionLocal() as new_db:
                    inter = new_db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
                    if inter:
                        inter.output_text = full_text.strip()
                        new_db.commit()
            except Exception as e:
                logger.error(f"Erro ao salvar interação final: {e}")
            
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

    # 4. Sintetizar áudio de resposta via Streaming ou Arquivo Único
    try:
        voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
        chosen_voice = voice_setting.value.strip() if voice_setting and voice_setting.value and voice_setting.value.strip() else "pt-BR-FranciscaNeural"

        tts_engine = get_tts_engine()
        tts_engine.reload_voice(chosen_voice)
        
        logger.info(f"Pipeline pré-TTS pronto em {_time.time() - t_pipeline_start:.3f}s")
        
        if not stream_tts:
            full_text = ""
            async for sentence in intercepted_stream:
                full_text += sentence + " "
            full_text = full_text.strip()
            
            if full_text:
                import tempfile
                tmp_wav = tempfile.mktemp(suffix=".wav")
                await tts_engine.synthesize_wav(full_text, tmp_wav)
                with open(tmp_wav, "rb") as f:
                    wav_data = f.read()
                os.remove(tmp_wav)
                
                try:
                    with SessionLocal() as new_db:
                        inter = new_db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
                        if inter:
                            inter.latency_ms = int((_time.time() - t_pipeline_start) * 1000)
                            new_db.commit()
                except Exception as e:
                    logger.error(f"Erro ao salvar latência do áudio completo: {e}")
                
                yield wav_data
        else:
            first_audio_chunk = True
            async for audio_chunk in tts_engine.stream_audio_from_generator(intercepted_stream):
                if first_audio_chunk:
                    try:
                        with SessionLocal() as new_db:
                            inter = new_db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
                            if inter:
                                inter.latency_ms = int((_time.time() - t_pipeline_start) * 1000)
                                new_db.commit()
                    except Exception as e:
                        logger.error(f"Erro ao salvar latência do chunk TTS: {e}")
                    first_audio_chunk = False
                yield audio_chunk
            
    except Exception as e:
        logger.error(f"Erro no TTS: {e}")