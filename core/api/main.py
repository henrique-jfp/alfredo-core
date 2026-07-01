from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Header
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import logging
import sys
import os
import time
import asyncio
from typing import Dict, Any

from core.services.scheduler import SchedulerManager

# Carrega as variáveis de ambiente (Groq, Auth, etc) ANTES de inicializar o resto
load_dotenv()

from core.brain.memory import models
from core.brain.memory.database import engine, get_db
from core.api import schemas
from core.voice.stt.engine import get_stt_engine
from core.voice.tts.engine import get_tts_engine
from core.brain.router import get_router
from core.api.dashboard import router as dashboard_router
from core.api.spotify import router as spotify_router

# Inicializa o banco (cria tabelas se não existirem)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Alfredo Home OS API", version="1.0.0")

active_connections: Dict[str, Any] = {}

def get_active_connections():
    return active_connections

scheduler = SchedulerManager(get_active_connections)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(scheduler.start())

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
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint principal para recepção de áudio dos satélites (Etapa 2).
    Por enquanto (Mock Phase), ele salva o áudio, registra a interação e retorna o mesmo áudio.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Bearer Token")
        
    if not x_device_id or not x_room_id:
        raise HTTPException(status_code=400, detail="Missing X-Device-ID or X-Room-ID headers")
        
    logger.info(f"Received audio from Device: {x_device_id} in Room: {x_room_id}")
    
    # 1. Salvar o áudio temporariamente
    temp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    input_filepath = os.path.join(temp_dir, f"in_{int(time.time())}.wav")
    
    with open(input_filepath, "wb") as buffer:
        buffer.write(await file.read())
        
    logger.info(f"Audio saved to {input_filepath}")
    
    # 2. Registrar interação no banco de dados (SQLite)
    interaction = models.Interaction(
        device_id=x_device_id,
        room_id=x_room_id,
        input_text=None, # Ainda sem Vosk
        output_text=None
    )
    db.add(interaction)
    db.commit()
    
    # 3. Pipeline de STT e TTS
    logger.info("Enviando áudio para o VOSK (STT)...")
    transcribed_text = ""
    try:
        stt_engine = get_stt_engine()
        transcribed_text = stt_engine.transcribe_wav(input_filepath)
        
        # Atualizar a interação com o texto reconhecido
        interaction.input_text = transcribed_text
        db.commit()
        
        logger.info(f"Usuário disse: {transcribed_text}")
    except Exception as e:
        logger.error(f"Erro no VOSK: {e}")

    # 4. Roteamento de Intenção e Execução de Skills (Etapa 3)
    logger.info("Enviando texto para o Router...")
    try:
        router = get_router()
        # O context pode ser enriquecido com os headers do dispositivo e fila de ws
        context = {
            "device_id": x_device_id,
            "room_id": x_room_id,
            "db": db,
            "ws_tasks": []
        }
        response_text = router.process(transcribed_text, context)
        
        # Dispara eventos WebSockets pendentes que as Skills colocaram na fila
        for task in context["ws_tasks"]:
            target_ws = active_connections.get(task["device_id"])
            if target_ws:
                await target_ws.send_json(task["payload"])
                logger.info(f"Push enviado via WebSocket para {task['device_id']}")
                
    except Exception as e:
        logger.error(f"Erro no Router: {e}")
        response_text = "Tive um problema interno ao tentar pensar na sua resposta."
    
    # 5. Sintetizar áudio de resposta com Piper
    output_filepath = os.path.join(temp_dir, f"out_{int(time.time())}.wav")
    try:
        # Busca a voz configurada no banco (se não houver, usa faber padrão)
        voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
        chosen_voice = voice_setting.value if voice_setting else "pt_BR-faber-medium"
        
        tts_engine = get_tts_engine()
        tts_engine.reload_voice(chosen_voice)
        tts_engine.synthesize_wav(response_text, output_filepath)
        
        interaction.output_text = response_text
        db.commit()
    except Exception as e:
        logger.error(f"Erro no Piper TTS: {e}")
        # Retorna erro genérico se falhar
        raise HTTPException(status_code=500, detail="Erro na síntese de voz.")
    
    return FileResponse(output_filepath, media_type="audio/wav")

from core.services.weather_service import get_current_weather
from fastapi import WebSocket, WebSocketDisconnect
from core.brain.memory.database import SessionLocal

@app.get("/api/weather/current")
def get_weather(db: Session = Depends(get_db)):
    """Retorna o clima atual (com cache) da cidade configurada."""
    return get_current_weather(db)

@app.websocket("/ws/satellite/{device_id}")
async def websocket_satellite(websocket: WebSocket, device_id: str):
    """Conexão persistente para atualizar o display da bolinha física."""
    await websocket.accept()
    logger.info(f"WebSocket conectado: {device_id}")
    active_connections[device_id] = websocket
    
    try:
        # 1. Enviar estado inicial (ex: Clima) logo após conectar
        db = SessionLocal()
        weather = get_current_weather(db)
        db.close()
        
        await websocket.send_json({
            "type": "weather_update",
            "data": weather
        })
        
        # 2. Loop para manter a conexão aberta (Servidor enviará push futuramente)
        while True:
            # O dispositivo pode mandar PING para manter a conexão ativa
            data = await websocket.receive_text()
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: {device_id}")
    finally:
        if device_id in active_connections:
            del active_connections[device_id]

# Adicionando o Router do Dashboard
app.include_router(dashboard_router)
app.include_router(spotify_router)

# Montando a pasta estática do frontend na URL raiz (/)
# ATENÇÃO: mount("/") deve ser o último para não sobrescrever as rotas /api/
dashboard_path = os.path.join(os.getcwd(), "dashboard", "frontend")
app.mount("/", StaticFiles(directory=dashboard_path, html=True), name="frontend")

@app.get("/api/audio/{filename}")
def get_audio(filename: str):
    """Endpoint para fornecer arquivos de áudio gerados pelo TTS para o hardware baixar."""
    temp_dir = os.path.join(os.getcwd(), "tmp")
    filepath = os.path.join(temp_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(filepath, media_type="audio/wav")
