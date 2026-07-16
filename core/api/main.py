from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Header
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import logging
import sys
import os
import time
import asyncio
from typing import Dict, Any
import urllib.parse

# Carrega as variáveis de ambiente (Groq, Auth, etc) ANTES de inicializar o resto
load_dotenv()

# Recarrega as chaves no key_manager AGORA que o .env foi carregado
from core.services.key_manager import reload_keys
reload_keys()

from core.services.scheduler import SchedulerManager

from core.brain.memory import models
from core.brain.memory.database import engine, get_db
from core.api import schemas
from core.voice.stt.engine import get_stt_engine
from core.voice.tts.engine import get_tts_engine
from core.brain.router import get_router
from core.api.dashboard import router as dashboard_router
from core.api.spotify import router as spotify_router
from core.api.satellite import router as satellite_ws_router
from core.api.satellite import rest_router as satellite_rest_router

# Inicializa o banco (cria tabelas se não existirem)
models.Base.metadata.create_all(bind=engine)

# Migrações automáticas de schema para SQLite local
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN reminders VARCHAR DEFAULT '60'"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN notified VARCHAR DEFAULT ''"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN google_event_id VARCHAR"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN google_updated VARCHAR"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE app_integrations ADD COLUMN token_data VARCHAR"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE memory_facts ADD COLUMN embedding VARCHAR"))
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE events ADD COLUMN source VARCHAR DEFAULT 'LOCAL' NOT NULL"))
        except Exception:
            pass
        conn.commit()
except Exception as e:
    logging.getLogger("alfredo.startup").error(f"Erro na migração do banco: {e}")

# Migração de dados legados (room_id='google_sync' → source='GOOGLE', room_id=None)
try:
    db_session = next(get_db())
    try:
        from core.services.calendar_service import migrate_legacy_events
        count = migrate_legacy_events(db_session)
        if count:
            logger = logging.getLogger("alfredo.startup")
            logger.info(f"Migração legada concluída: {count} eventos corrigidos")
    except Exception as e:
        logging.getLogger("alfredo.startup").error(f"Erro na migração de dados legados: {e}")
    finally:
        db_session.close()
except Exception as e:
    logging.getLogger("alfredo.startup").error(f"Erro ao abrir sessão para migração: {e}")

# Sincroniza .env → DB (para quem já configurou pelo .env)
from core.services.env_manager import sync_env_to_db
_env_vars = sync_env_to_db()
if _env_vars.get("SPOTIFY_CLIENT_ID") or _env_vars.get("SPOTIFY_CLIENT_SECRET"):
    db_session = next(get_db())
    try:
        spotify = db_session.query(models.AppIntegration).filter(
            models.AppIntegration.app_name == "spotify"
        ).first()
        env_id = _env_vars.get("SPOTIFY_CLIENT_ID", "")
        env_secret = _env_vars.get("SPOTIFY_CLIENT_SECRET", "")
        db_id = spotify.client_id if spotify else ""
        db_secret = spotify.client_secret if spotify else ""

        if env_id != db_id or env_secret != db_secret:
            if not spotify:
                spotify = models.AppIntegration(
                    app_name="spotify",
                    client_id=env_id,
                    client_secret=env_secret,
                    is_connected=False
                )
                db_session.add(spotify)
            else:
                spotify.client_id = env_id
                spotify.client_secret = env_secret
            db_session.commit()
            logger = logging.getLogger("alfredo.startup")
            logger.info("Credenciais Spotify sincronizadas do .env para o DB")
    except Exception:
        pass
    finally:
        db_session.close()

app = FastAPI(title="Alfredo Home OS API", version="1.0.0")

from core.api.satellite import manager

def get_active_connections():
    return manager.active_satellites

scheduler = SchedulerManager(get_active_connections)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduler.start())
    # Warm up TTS cache for fast routing responses
    from core.brain.routers import ROUTES
    from core.voice.tts.engine import get_tts_engine
    fixed_responses = [r.response for r in ROUTES if r.response]
    if fixed_responses:
        logger.info("Aquecendo cache TTS para respostas rápidas...")
        tts_engine = get_tts_engine()
        asyncio.create_task(tts_engine.warm_cache(fixed_responses))
@app.on_event("shutdown")
def shutdown_event():
    scheduler.stop()

# Configurar o logger para aparecer junto com o Uvicorn
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t%(name)s - %(message)s", stream=sys.stdout)
logger = logging.getLogger("alfredo.api")
logger.setLevel(logging.INFO)

@app.post("/api/devices/register", response_model=schemas.DeviceRegisterResponse)
def register_device(payload: schemas.DeviceRegisterRequest, db: Session = Depends(get_db)):
    """
    Endpoint para registro de novos satélites ou atualização de estado de satélites existentes no boot.
    A arquitetura multi-hardware usa o campo 'capabilities' para definir como o servidor interage com o device.
    """
    
    #TODO: Implementar verificação do Bearer token (SATELLITE_AUTH_TOKEN)
    
    device = db.query(models.Device).filter(models.Device.device_id == payload.device_id).first()
    
    if not device:
        # Cria um novo dispositivo
        device = models.Device(
            device_id=payload.device_id,
            room_id=payload.room_id,
            hardware=payload.hardware,
            firmware_version=payload.firmware_version,
            capabilities=payload.capabilities
        )
        db.add(device)
        logger.info(f"New device registered: {payload.device_id} ({payload.hardware})")
    else:
        # Atualiza dispositivo existente
        device.room_id = payload.room_id
        device.hardware = payload.hardware
        device.firmware_version = payload.firmware_version
        device.capabilities = payload.capabilities
        logger.info(f"Device updated: {payload.device_id}")

    db.commit()
    
    return schemas.DeviceRegisterResponse(
        status="registered",
        message="Welcome to Alfredo Home OS"
    )

@app.post("/api/voice")
async def process_voice(
    file: UploadFile = File(...),
    x_device_id: str = Header(None),
    x_room_id: str = Header(None),
    x_vosk_text: str = Header(None),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para recepção de áudio dos satélites.
    Otimizado para latência mínima: processa em memória, streaming real.
    """
    import time as _time
    t_pipeline_start = _time.time()
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer Token")
        
    if not x_device_id or not x_room_id:
        raise HTTPException(status_code=400, detail="Missing X-Device-ID or X-Room-ID headers")
        
    logger.info(f"Received audio from Device: {x_device_id} in Room: {x_room_id}")
    
    # 1. Ler áudio em memória (sem salvar em disco — elimina ~100ms de I/O)
    audio_bytes = await file.read()
    logger.info(f"Áudio recebido via POST: {len(audio_bytes)} bytes ({_time.time() - t_pipeline_start:.3f}s)")
    
    from core.voice.pipeline import process_audio_pipeline
    from core.voice.tts.engine import get_tts_engine
    
    # Verificamos se é webm baseando-se no filename ou header (por padrão POST file enviamos do virtual mic)
    is_webm = False
    if file.filename and file.filename.endswith('.webm'):
        is_webm = True
        
    vosk_text = urllib.parse.unquote(x_vosk_text) if x_vosk_text else ""
    generator = process_audio_pipeline(audio_bytes, x_device_id, x_room_id, db, is_webm=is_webm, vosk_text=vosk_text)

    tts_engine = get_tts_engine()
    return StreamingResponse(
        generator,
        media_type=tts_engine.media_type
    )

@app.post("/api/voice/transcribe")
async def process_voice_transcribe(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    """
    Endpoint leve apenas para STT. Usado pelo satélite para detecção contínua usando Whisper.
    """
    temp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".wav"
    if not ext:
        ext = ".wav"
    input_filepath = os.path.join(temp_dir, f"transcribe_{int(time.time())}{ext}")
    
    with open(input_filepath, "wb") as buffer:
        buffer.write(await file.read())
        
    try:
        stt_engine = get_stt_engine()
        transcribed_text = stt_engine.transcribe_wav(input_filepath)
        return {"text": transcribed_text}
    except Exception as e:
        logger.error(f"Erro no VOSK/Whisper: {e}")
        return {"text": ""}

from pydantic import BaseModel

class TextCommandRequest(BaseModel):
    text: str
    device_id: str = "dashboard-virtual-mic"
    room_id: str = "ROOM_LIVING"
    play_locally: bool = False

@app.post("/api/voice/text")
async def process_voice_text(
    payload: TextCommandRequest,
    db: Session = Depends(get_db)
):
    """
    Endpoint para envio de comandos de texto via Dashboard (Virtual Mic).
    Retorna o arquivo de áudio de resposta.
    """
    logger.info(f"Comando de texto via Dashboard: {payload.text}")
    
    # 1. Registrar interação
    interaction = models.Interaction(
        device_id=payload.device_id,
        room_id=payload.room_id,
        input_text=payload.text,
        output_text=None
    )
    db.add(interaction)
    db.commit()
    
    # 2. Roteamento e execução
    try:
        router = get_router()
        context = {
            "device_id": payload.device_id,
            "room_id": payload.room_id,
            "db": db,
            "ws_tasks": []
        }
        response_text = router.process(payload.text, context)
        
        for task in context["ws_tasks"]:
            target_ws = active_connections.get(task["device_id"])
            if target_ws:
                await target_ws.send_json(task["payload"])
                
    except Exception as e:
        logger.error(f"Erro no Router (Text): {e}")
        response_text = "Tive um problema interno ao processar o texto."
        
    # 3. Sintetizar áudio
    temp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    output_filepath = os.path.join(temp_dir, f"out_text_{int(time.time())}.wav")
    
    try:
        voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
        chosen_voice = voice_setting.value.strip() if voice_setting and voice_setting.value and voice_setting.value.strip() else "pt-BR-FranciscaNeural"

        tts_engine = get_tts_engine()
        tts_engine.reload_voice(chosen_voice)
        await tts_engine.synthesize_wav(response_text, output_filepath)
        
        interaction.output_text = response_text
        db.commit()
        
        if payload.play_locally:
            import subprocess
            # Play on the server using ffplay
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", output_filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"status": "playing_locally", "text": response_text}
            
    except Exception as e:
        logger.error(f"Erro no Piper TTS (Text): {e}")
        raise HTTPException(status_code=500, detail="Erro na síntese de voz.")
        
    return FileResponse(output_filepath, media_type="audio/wav")

from core.services.weather_service import get_current_weather
from fastapi import WebSocket, WebSocketDisconnect
from core.brain.memory.database import SessionLocal

@app.get("/api/session-status")
def session_status(room_id: str, db: Session = Depends(get_db)):
    """Retorna se há uma sessão ativa (quiz, receita, etc.) para a sala."""
    session = db.query(models.SessionState).filter(
        models.SessionState.room_id == room_id
    ).first()
    return {
        "active": session is not None,
        "skill": session.skill_name if session else None
    }

@app.get("/api/weather/current")
def get_weather(db: Session = Depends(get_db)):
    """Retorna o clima atual (com cache) da cidade configurada."""
    return get_current_weather(db)

@app.get("/api/weather/forecast")
def get_weather_forecast(db: Session = Depends(get_db)):
    """Retorna a previsão estendida (atual + 5 dias)."""
    from core.services.weather_service import get_forecast
    return get_forecast(db)


# Adicionando o Router do Dashboard
app.include_router(dashboard_router)
app.include_router(spotify_router)
app.include_router(satellite_ws_router)
app.include_router(satellite_rest_router)

from core.api.tv import router as tv_router
app.include_router(tv_router)

from core.api.google_auth import router as google_auth_router
app.include_router(google_auth_router)

from core.api.smart_home import router as smart_home_router
app.include_router(smart_home_router)

@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    """Endpoint para fornecer arquivos de áudio gerados pelo TTS para o hardware baixar."""
    temp_dir = os.path.join(os.getcwd(), "tmp")
    filepath = os.path.join(temp_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath, media_type="audio/wav")

# Montando a pasta estática do frontend na URL raiz (/)
# ATENÇÃO: mount("/") deve ser o último para não sobrescrever as rotas /api/
dashboard_path = os.path.join(os.getcwd(), "dashboard", "frontend")
app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="frontend")
