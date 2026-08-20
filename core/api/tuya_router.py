from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from core.brain.memory.database import get_db
from core.brain.memory import models
from core.services.tuya_hub import tuya_hub_manager
from pydantic import BaseModel
import logging

logger = logging.getLogger("alfredo.api.tuya")

router = APIRouter(prefix="/api/tuya", tags=["tuya"])

class TuyaHubCreate(BaseModel):
    device_id: str
    ip_address: str
    local_key: str
    name: str
    room_id: str
    version: str = "3.3"

class TuyaCommandCreate(BaseModel):
    hub_id: int
    command_name: str
    device_type: str
    protocol: str
    payload_base64: str
    room_id: str

@router.get("/hubs")
def get_hubs(db: Session = Depends(get_db)):
    hubs = db.query(models.TuyaHub).all()
    return hubs

@router.post("/hubs")
def create_hub(hub: TuyaHubCreate, db: Session = Depends(get_db)):
    db_hub = models.TuyaHub(**hub.dict())
    db.add(db_hub)
    db.commit()
    db.refresh(db_hub)
    return db_hub

@router.get("/commands")
def get_commands(db: Session = Depends(get_db)):
    return db.query(models.TuyaCommand).all()

@router.post("/commands")
def create_command(cmd: TuyaCommandCreate, db: Session = Depends(get_db)):
    db_cmd = models.TuyaCommand(**cmd.dict())
    db.add(db_cmd)
    db.commit()
    db.refresh(db_cmd)
    return db_cmd

@router.post("/learn/{hub_id}")
def learn_command(hub_id: int, protocol: str = "rf", db: Session = Depends(get_db)):
    hub = db.query(models.TuyaHub).filter(models.TuyaHub.id == hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub not found")
    
    if protocol.lower() == "rf":
        payload = tuya_hub_manager.learn_rf(hub.device_id, hub.ip_address, hub.local_key, freq=433, version=hub.version, timeout=20)
    else:
        payload = tuya_hub_manager.learn_ir(hub.device_id, hub.ip_address, hub.local_key, version=hub.version, timeout=20)
        
    if not payload:
        raise HTTPException(status_code=400, detail="Failed to learn command. Try again.")
        
    return {"payload_base64": payload}

@router.post("/send/{command_id}")
def send_command(command_id: int, db: Session = Depends(get_db)):
    cmd = db.query(models.TuyaCommand).filter(models.TuyaCommand.id == command_id).first()
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
        
    hub = db.query(models.TuyaHub).filter(models.TuyaHub.id == cmd.hub_id).first()
    if not hub:
        raise HTTPException(status_code=404, detail="Hub not found")
        
    if cmd.protocol.lower() == "rf":
        success = tuya_hub_manager.send_rf(hub.device_id, hub.ip_address, hub.local_key, cmd.payload_base64, version=hub.version)
    else:
        success = tuya_hub_manager.send_ir(hub.device_id, hub.ip_address, hub.local_key, cmd.payload_base64, version=hub.version)
        
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send command")
        
    return {"status": "ok"}
