from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
from sqlalchemy.orm import Session
from core.brain.memory import models
from core.brain.memory.database import get_db

router = APIRouter(prefix="/api/ws", tags=["WebSockets"])

class ConnectionManager:
    def __init__(self):
        # { "device_id": WebSocket }
        self.active_satellites: Dict[str, WebSocket] = {}
        # List of Dashboard clients (listeners)
        self.dashboard_clients: List[WebSocket] = []

    async def connect_satellite(self, websocket: WebSocket, device_id: str):
        await websocket.accept()
        self.active_satellites[device_id] = websocket

    def disconnect_satellite(self, device_id: str):
        if device_id in self.active_satellites:
            del self.active_satellites[device_id]

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_clients.append(websocket)

    def disconnect_dashboard(self, websocket: WebSocket):
        if websocket in self.dashboard_clients:
            self.dashboard_clients.remove(websocket)

    async def broadcast_to_dashboards(self, data: bytes):
        for client in self.dashboard_clients:
            try:
                await client.send_bytes(data)
            except:
                pass

    async def send_command_to_satellite(self, device_id: str, command: str, payload: dict = None):
        if device_id in self.active_satellites:
            try:
                import json
                msg = {"type": command}
                if payload:
                    msg.update(payload)
                await self.active_satellites[device_id].send_text(json.dumps(msg))
                return True
            except:
                return False
        return False

manager = ConnectionManager()

@router.websocket("/satellite/{device_id}")
async def websocket_satellite_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect_satellite(websocket, device_id)
    try:
        while True:
            # Satellites will send raw PCM or WAV chunks
            data = await websocket.receive_bytes()
            # Forward audio chunks immediately to all connected dashboard listeners
            await manager.broadcast_to_dashboards(data)
    except WebSocketDisconnect:
        manager.disconnect_satellite(device_id)
    except Exception as e:
        manager.disconnect_satellite(device_id)

@router.websocket("/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Receive commands from dashboard (e.g. "START_STREAM:device_id")
            data = await websocket.receive_text()
            parts = data.split(":")
            command = parts[0]
            device_id = parts[1] if len(parts) > 1 else None
            
            if not device_id:
                continue

            if command == "START_STREAM":
                await manager.send_command_to_satellite(device_id, "START_STREAM")
            elif command == "STOP_STREAM":
                await manager.send_command_to_satellite(device_id, "STOP_STREAM")
            elif command == "IDENTIFY":
                await manager.send_command_to_satellite(device_id, "IDENTIFY")
            elif command == "OTA_UPDATE":
                await manager.send_command_to_satellite(device_id, "OTA_UPDATE")
            elif command == "SET_VOLUME" and len(parts) > 2:
                volume = int(parts[2])
                # Save to DB
                device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
                if device:
                    device.volume = volume
                    db.commit()
                await manager.send_command_to_satellite(device_id, "SET_VOLUME", {"value": volume})
            elif command == "SET_BRIGHTNESS" and len(parts) > 2:
                brightness = int(parts[2])
                # Save to DB
                device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
                if device:
                    device.brightness = brightness
                    db.commit()
                await manager.send_command_to_satellite(device_id, "SET_BRIGHTNESS", {"value": brightness})
            elif command == "SET_ALSA_CAPTURE" and len(parts) > 2:
                val = parts[2]
                await manager.send_command_to_satellite(device_id, "SET_ALSA_CAPTURE", {"value": val})
            elif command == "SET_ALSA_MASTER" and len(parts) > 2:
                val = parts[2]
                await manager.send_command_to_satellite(device_id, "SET_ALSA_MASTER", {"value": val})
            elif command == "SET_SOFTWARE_PREAMP" and len(parts) > 2:
                val = parts[2]
                await manager.send_command_to_satellite(device_id, "SET_SOFTWARE_PREAMP", {"value": val})
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
    except Exception as e:
        manager.disconnect_dashboard(websocket)

# Endpoint to list connected satellites (REST)
rest_router = APIRouter(prefix="/api/satellite", tags=["Satellite Control"])

@rest_router.get("/connected")
def get_connected_satellites():
    return {"connected": list(manager.active_satellites.keys())}

@rest_router.get("/devices")
def get_all_devices(db: Session = Depends(get_db)):
    devices = db.query(models.Device).all()
    result = []
    active_ws = set(manager.active_satellites.keys())
    
    for d in devices:
        result.append({
            "device_id": d.device_id,
            "room_id": d.room_id,
            "hardware": d.hardware,
            "firmware_version": d.firmware_version,
            "capabilities": d.capabilities,
            "volume": d.volume,
            "brightness": d.brightness,
            "is_online": d.device_id in active_ws
        })
    return result
