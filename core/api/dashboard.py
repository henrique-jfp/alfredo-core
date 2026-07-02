from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import socket
import os
import time
from sqlalchemy import func
from core.brain.memory import models
from core.brain.memory.database import get_db
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Retorna estatísticas gerais do sistema para os cartões (KPIs)."""
    # Total de interações realizadas
    total_interactions = db.query(models.Interaction).count()
    
    # Satélites/Dispositivos cadastrados
    devices_registered = db.query(models.Device).count()
    
    # Quantidade de cronômetros rodando no momento
    active_timers = db.query(models.Timer).filter(models.Timer.is_active == True).count()
    
    # Soma de tokens processados pela IA
    tokens_used_query = db.query(func.sum(models.AIUsage.tokens_used)).scalar()
    tokens_used = tokens_used_query if tokens_used_query else 0
    
    return {
        "interactions": total_interactions,
        "devices": devices_registered,
        "active_timers": active_timers,
        "tokens_used": tokens_used
    }

@router.get("/history")
def get_history(limit: int = 15, db: Session = Depends(get_db)):
    """Retorna o histórico de conversas do assistente."""
    # Filtra interações vazias (quando o STT não escuta nada)
    history = db.query(models.Interaction).filter(
        models.Interaction.input_text != None,
        models.Interaction.input_text != ""
    ).order_by(models.Interaction.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": item.id,
            "room_id": item.room_id,
            "device_id": item.device_id,
            "input_text": item.input_text,
            "output_text": item.output_text,
            "timestamp": item.timestamp.isoformat() if item.timestamp else None
        } for item in history
    ]

@router.get("/lists")
def get_lists(db: Session = Depends(get_db)):
    """Retorna as listas de compras e tarefas atuais."""
    items = db.query(models.ListItem).order_by(models.ListItem.created_at.desc()).all()
    
    compras = []
    tarefas = []
    
    for item in items:
        obj = {
            "id": item.id,
            "content": item.content,
            "room_id": item.room_id,
            "created_at": item.created_at.isoformat() if item.created_at else None
        }
        if item.list_type == "compras":
            compras.append(obj)
        else:
            tarefas.append(obj)
            
    return {
        "compras": compras,
        "tarefas": tarefas
    }

@router.get("/timers")
def get_timers(db: Session = Depends(get_db)):
    """Retorna todos os timers e lembretes ativos."""
    timers = db.query(models.Timer).filter(models.Timer.is_active == True).order_by(models.Timer.expires_at.asc()).all()
    
    return [
        {
            "id": t.id,
            "room_id": t.room_id,
            "duration_seconds": t.duration_seconds,
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "message": t.message,
            "timer_type": t.timer_type
        } for t in timers
    ]

@router.delete("/timers/{timer_id}")
def delete_timer(timer_id: int, db: Session = Depends(get_db)):
    """Exclui ou cancela um timer ativo."""
    timer = db.query(models.Timer).filter(models.Timer.id == timer_id).first()
    if timer:
        db.delete(timer)
        db.commit()
    return {"status": "success"}

class SpotifyCredentials(BaseModel):
    client_id: str
    client_secret: str

@router.get("/integrations")
def get_integrations(db: Session = Depends(get_db)):
    """Retorna o status das integrações e o IP local."""
    spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
    
    # Tenta descobrir o IP real da máquina na rede local para o QR Code
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()
        
    return {
        "local_ip": local_ip,
        "spotify": {
            "is_configured": spotify is not None and bool(spotify.client_id),
            "is_connected": spotify.is_connected if spotify else False
        }
    }

@router.post("/integrations/spotify/save")
def save_spotify_keys(creds: SpotifyCredentials, db: Session = Depends(get_db)):
    spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
    if not spotify:
        spotify = models.AppIntegration(
            app_name="spotify",
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            is_connected=False
        )
        db.add(spotify)
    else:
        spotify.client_id = creds.client_id
        spotify.client_secret = creds.client_secret
        spotify.is_connected = False
        
    db.commit()
    return {"status": "success"}

# --- ROTINAS ---

class RoutineCreate(BaseModel):
    name: str
    trigger_type: str
    trigger_value: str
    action_type: str
    action_value: str
    room_id: str
    
@router.get("/routines")
def get_routines(db: Session = Depends(get_db)):
    """Retorna todas as rotinas."""
    routines = db.query(models.Routine).order_by(models.Routine.created_at.desc()).all()
    return routines

@router.post("/routines")
def create_routine(payload: RoutineCreate, db: Session = Depends(get_db)):
    """Cria uma nova rotina."""
    new_routine = models.Routine(
        name=payload.name,
        trigger_type=payload.trigger_type,
        trigger_value=payload.trigger_value,
        action_type=payload.action_type,
        action_value=payload.action_value,
        room_id=payload.room_id
    )
    db.add(new_routine)
    db.commit()
    db.refresh(new_routine)
    return new_routine

@router.delete("/routines/{routine_id}")
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    """Exclui uma rotina."""
    routine = db.query(models.Routine).filter(models.Routine.id == routine_id).first()
    if routine:
        db.delete(routine)
        db.commit()
    return {"status": "success"}

@router.post("/routines/{routine_id}/test")
def test_routine(routine_id: int, db: Session = Depends(get_db)):
    """Dispara a rotina instantaneamente para testes (simulando a condição de tempo)."""
    routine = db.query(models.Routine).filter(models.Routine.id == routine_id).first()
    if not routine:
        return {"error": "Routine not found"}
        
    # Zera a data de last_run para que o scheduler rode no próximo segundo
    # Para testes imediatos, simplesmente mudamos o last_run e o trigger_value pro HH:MM atual
    from datetime import datetime
    now = datetime.now()
    routine.trigger_value = now.strftime("%H:%M")
    return {"status": "success", "message": "A rotina foi ajustada para rodar agora!"}

# --- CONFIGURAÇÕES ---

class SettingsPayload(BaseModel):
    settings: dict
    
@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Retorna todas as configurações."""
    settings = db.query(models.Setting).all()
    # Converte de lista de models para um dict simples {key: value}
    settings_dict = {s.key: s.value for s in settings}
    return settings_dict

@router.post("/settings")
async def save_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    """Salva um dicionário de configurações e avisa satélites se o nome mudar."""
    name_changed = False
    new_name = ""
    
    for key, value in payload.settings.items():
        setting = db.query(models.Setting).filter(models.Setting.key == key).first()
        if setting:
            if key == "assistant_name" and setting.value != value:
                name_changed = True
                new_name = value
            setting.value = value
        else:
            if key == "assistant_name":
                name_changed = True
                new_name = value
            new_setting = models.Setting(key=key, value=value)
            db.add(new_setting)
            
    db.commit()
    
    # Se o nome do assistente mudou, avisa todos os satélites via WebSocket
    if name_changed:
        from core.api.main import get_active_connections
        active_conns = get_active_connections()
        for device_id, ws in active_conns.items():
            try:
                await ws.send_json({
                    "type": "update_wake_word",
                    "wake_word": new_name
                })
            except Exception:
                pass
                
    return {"status": "success"}

class VoiceTestPayload(BaseModel):
    voice_name: str

@router.post("/tts/test")
async def test_tts(payload: VoiceTestPayload):
    """Testa uma voz específica e retorna o áudio."""
    from core.voice.tts.engine import get_tts_engine
    
    temp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    output_filepath = os.path.join(temp_dir, f"test_{int(time.time())}.wav")
    
    try:
        # A TTSEngine foi atualizada para aceitar troca de voz dinâmica via nuvem
        tts = get_tts_engine()
        tts.reload_voice(payload.voice_name)
        await tts.synthesize_wav("Olá, eu sou o seu assistente. Como posso ajudar hoje?", output_filepath)
        return FileResponse(output_filepath, media_type="audio/wav")
    except Exception as e:
        return {"error": str(e)}

# --- ENDEREÇOS SALVOS ---

class LocationCreate(BaseModel):
    name: str
    latitude: str
    longitude: str
    icon: str = "pin"

@router.get("/locations")
def get_locations(db: Session = Depends(get_db)):
    """Retorna todos os endereços salvos."""
    locations = db.query(models.SavedLocation).order_by(models.SavedLocation.created_at.desc()).all()
    return [
        {
            "id": loc.id,
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "icon": loc.icon,
            "created_at": loc.created_at.isoformat() if loc.created_at else None
        } for loc in locations
    ]

@router.post("/locations")
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    """Cria um novo endereço salvo."""
    new_loc = models.SavedLocation(
        name=payload.name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        icon=payload.icon
    )
    db.add(new_loc)
    db.commit()
    db.refresh(new_loc)
    return {"status": "success", "id": new_loc.id}

@router.delete("/locations/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """Exclui um endereço salvo."""
    loc = db.query(models.SavedLocation).filter(models.SavedLocation.id == location_id).first()
    if loc:
        db.delete(loc)
        db.commit()
    return {"status": "success"}

# --- TOGGLE ROTINA ---

@router.patch("/routines/{routine_id}/toggle")
def toggle_routine(routine_id: int, db: Session = Depends(get_db)):
    """Ativa/desativa uma rotina."""
    routine = db.query(models.Routine).filter(models.Routine.id == routine_id).first()
    if not routine:
        return {"error": "Routine not found"}
    routine.is_active = not routine.is_active
    db.commit()
    return {"status": "success", "is_active": routine.is_active}
