"""
API REST para gerenciamento de cômodos (rooms) e dispositivos inteligentes
(smart_devices). Segue o mesmo padrão de core/api/tv.py.

Endpoints:
  /api/rooms          — GET (listar), POST (criar)
  /api/rooms/{id}     — PUT, DELETE
  /api/smart-devices  — GET (listar por room_id), POST (criar)
  /api/smart-devices/{id} — PUT, DELETE
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from core.brain.memory.database import get_db
from core.brain.memory import models

router = APIRouter(prefix="/api", tags=["smart_home"])

# ── Schemas ────────────────────────────────────────────────────────────

class RoomCreate(BaseModel):
    room_id: str
    name: str

class RoomUpdate(BaseModel):
    name: Optional[str] = None

class RoomResponse(BaseModel):
    id: int
    room_id: str
    name: str

    class Config:
        from_attributes = True

class SmartDeviceCreate(BaseModel):
    entity_id: str
    friendly_name: str
    device_type: str  # "light", "fan", "switch", "lock", "sensor"
    room_id: str
    is_active: bool = True

class SmartDeviceUpdate(BaseModel):
    friendly_name: Optional[str] = None
    device_type: Optional[str] = None
    room_id: Optional[str] = None
    is_active: Optional[bool] = None

class SmartDeviceResponse(BaseModel):
    id: int
    entity_id: str
    friendly_name: str
    device_type: str
    room_id: str
    is_active: bool

    class Config:
        from_attributes = True

# ── Rooms ──────────────────────────────────────────────────────────────

@router.get("/rooms", response_model=List[RoomResponse])
def list_rooms(db: Session = Depends(get_db)):
    """Lista todos os cômodos cadastrados."""
    return db.query(models.Room).order_by(models.Room.name).all()

@router.post("/rooms", response_model=RoomResponse)
def create_room(req: RoomCreate, db: Session = Depends(get_db)):
    """Cria um novo cômodo."""
    existing = db.query(models.Room).filter(
        models.Room.room_id == req.room_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Cômodo '{req.room_id}' já existe.")
    room = models.Room(room_id=req.room_id, name=req.name)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

@router.put("/rooms/{room_id}", response_model=RoomResponse)
def update_room(room_id: str, req: RoomUpdate, db: Session = Depends(get_db)):
    """Atualiza um cômodo existente."""
    room = db.query(models.Room).filter(models.Room.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Cômodo não encontrado.")
    if req.name is not None:
        room.name = req.name
    db.commit()
    db.refresh(room)
    return room

@router.delete("/rooms/{room_id}")
def delete_room(room_id: str, db: Session = Depends(get_db)):
    """Remove um cômodo e seus dispositivos associados."""
    room = db.query(models.Room).filter(models.Room.room_id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Cômodo não encontrado.")
    # Remove dispositivos ligados a este cômodo
    db.query(models.SmartDevice).filter(
        models.SmartDevice.room_id == room_id
    ).delete()
    db.delete(room)
    db.commit()
    return {"status": "deleted"}

# ── Smart Devices ──────────────────────────────────────────────────────

@router.get("/smart-devices", response_model=List[SmartDeviceResponse])
def list_smart_devices(
    room_id: Optional[str] = None,
    device_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Lista dispositivos inteligentes. Filtros opcionais: room_id, device_type."""
    q = db.query(models.SmartDevice)
    if room_id:
        q = q.filter(models.SmartDevice.room_id == room_id)
    if device_type:
        q = q.filter(models.SmartDevice.device_type == device_type)
    return q.order_by(models.SmartDevice.friendly_name).all()

@router.post("/smart-devices", response_model=SmartDeviceResponse)
def create_smart_device(req: SmartDeviceCreate, db: Session = Depends(get_db)):
    """Cadastra um novo dispositivo inteligente."""
    # Verifica se o cômodo existe
    room = db.query(models.Room).filter(models.Room.room_id == req.room_id).first()
    if not room:
        raise HTTPException(
            status_code=400,
            detail=f"Cômodo '{req.room_id}' não encontrado. Crie o cômodo primeiro.",
        )
    existing = db.query(models.SmartDevice).filter(
        models.SmartDevice.entity_id == req.entity_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Dispositivo '{req.entity_id}' já cadastrado.")
    dev = models.SmartDevice(
        entity_id=req.entity_id,
        friendly_name=req.friendly_name,
        device_type=req.device_type,
        room_id=req.room_id,
        is_active=req.is_active,
    )
    db.add(dev)
    db.commit()
    db.refresh(dev)
    return dev

@router.put("/smart-devices/{device_id}", response_model=SmartDeviceResponse)
def update_smart_device(
    device_id: int,
    req: SmartDeviceUpdate,
    db: Session = Depends(get_db),
):
    """Atualiza um dispositivo inteligente."""
    dev = db.query(models.SmartDevice).filter(models.SmartDevice.id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")
    if req.friendly_name is not None:
        dev.friendly_name = req.friendly_name
    if req.device_type is not None:
        dev.device_type = req.device_type
    if req.room_id is not None:
        room = db.query(models.Room).filter(models.Room.room_id == req.room_id).first()
        if not room:
            raise HTTPException(status_code=400, detail=f"Cômodo '{req.room_id}' não encontrado.")
        dev.room_id = req.room_id
    if req.is_active is not None:
        dev.is_active = req.is_active
    db.commit()
    db.refresh(dev)
    return dev

@router.delete("/smart-devices/{device_id}")
def delete_smart_device(device_id: int, db: Session = Depends(get_db)):
    """Remove um dispositivo inteligente."""
    dev = db.query(models.SmartDevice).filter(models.SmartDevice.id == device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")
    db.delete(dev)
    db.commit()
    return {"status": "deleted"}
