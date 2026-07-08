import os
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

async def process_audio_pipeline(audio_bytes: bytes, device_id: str, room_id: str, db: Session, is_webm: bool = False, stream_tts: bool = True) -> AsyncGenerator[bytes, None]:
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
    
    # 2. STT em memória
    t_stt_start = _time.time()
    transcribed_text = ""
    try:
        stt_engine = get_stt_engine()
        if hasattr(stt_engine, 'transcribe_bytes'):
            # FIX DE LATÊNCIA: antes, áudio webm era escrito em disco e passava
            # por uma conversão via ffmpeg (subprocess bloqueante) antes de ir
            # pro Groq. A API do Groq aceita webm/ogg/mp3 diretamente — então
            # agora mandamos os bytes originais direto em memória, sem
            # subprocess e sem I/O de disco, tanto pra wav quanto pra webm.
            if is_webm:
                transcribed_text = stt_engine.transcribe_bytes(audio_bytes, filename="audio.webm")
            else:
                import io, wave
                with io.BytesIO() as wav_io:
                    with wave.open(wav_io, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)
                        wav_file.writeframes(audio_bytes)
                    wav_bytes = wav_io.getvalue()
                transcribed_text = stt_engine.transcribe_bytes(wav_bytes)
        else:
            temp_dir = os.path.join(os.getcwd(), "tmp")
            os.makedirs(temp_dir, exist_ok=True)
            ext = ".webm" if is_webm else ".wav"
            input_filepath = os.path.join(temp_dir, f"in_{int(_time.time())}{ext}")
            with open(input_filepath, "wb") as buffer:
                buffer.write(audio_bytes)
            transcribed_text = stt_engine.transcribe_wav(input_filepath)
        
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
        # Silence or unrecognized
        return

    # 3. Roteamento de Intenção (Streaming Real)
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
                
            # Salvar no DB usando uma NOVA sessão para evitar detached instance / lock errors
            try:
                latency = int((_time.time() - t_pipeline_start) * 1000)
                with SessionLocal() as new_db:
                    inter = new_db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
                    if inter:
                        inter.output_text = full_text.strip()
                        inter.latency_ms = latency
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
                yield wav_data
        else:
            async for audio_chunk in tts_engine.stream_audio_from_generator(intercepted_stream):
                yield audio_chunk
            
    except Exception as e:
        logger.error(f"Erro no TTS: {e}")