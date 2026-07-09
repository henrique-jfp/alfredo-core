from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from core.brain.memory.database import get_db
from core.brain.memory import models
from core.services.samsung_tv import SamsungTVManager

router = APIRouter(prefix="/api/tv", tags=["tv"])

class TVConfigRequest(BaseModel):
    room_id: str
    ip_address: str = None
    mac_address: str = None
    smartthings_pat: str = None
    smartthings_device_id: str = None

@router.get("/config/{room_id}")
def get_tv_config(room_id: str, db: Session = Depends(get_db)):
    config = db.query(models.TVConfig).filter(models.TVConfig.room_id == room_id).first()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "room_id": config.room_id,
        "ip_address": config.ip_address,
        "mac_address": config.mac_address,
        "smartthings_pat": config.smartthings_pat,
        "smartthings_device_id": config.smartthings_device_id
    }

@router.post("/config")
def save_tv_config(req: TVConfigRequest, db: Session = Depends(get_db)):
    config = db.query(models.TVConfig).filter(models.TVConfig.room_id == req.room_id).first()
    if not config:
        config = models.TVConfig(room_id=req.room_id)
        db.add(config)
    
    config.ip_address = req.ip_address
    config.mac_address = req.mac_address
    config.smartthings_pat = req.smartthings_pat
    config.smartthings_device_id = req.smartthings_device_id
    db.commit()
    return {"status": "success"}

def _get_tv_manager(room_id: str, db: Session):
    config = db.query(models.TVConfig).filter(models.TVConfig.room_id == room_id).first()
    if not config or not config.ip_address:
        raise HTTPException(status_code=400, detail="TV not configured for this room")
    return SamsungTVManager(
        ip=config.ip_address,
        mac=config.mac_address,
        smartthings_pat=config.smartthings_pat,
        smartthings_device_id=config.smartthings_device_id
    )

@router.post("/control/{room_id}/mute")
async def tv_mute(room_id: str, state: bool, db: Session = Depends(get_db)):
    # Quick endpoint used by local_satellite to auto-mute
    tv = _get_tv_manager(room_id, db)
    await tv.set_mute(state)
    return {"status": "success"}

@router.post("/control/{room_id}/power")
async def tv_power(room_id: str, db: Session = Depends(get_db)):
    tv = _get_tv_manager(room_id, db)
    # sending POWER key usually toggles power on modern samsungs, or use WOL
    await tv.send_key("KEY_POWER")
    await tv.power_on()
    return {"status": "success"}

@router.post("/control/{room_id}/app")
async def tv_open_app(room_id: str, app_id: str, db: Session = Depends(get_db)):
    tv = _get_tv_manager(room_id, db)
    await tv.open_app(app_id)
    return {"status": "success"}

@router.get("/status/{room_id}")
async def tv_status(room_id: str, db: Session = Depends(get_db)):
    tv = _get_tv_manager(room_id, db)
    return await tv.get_status()
