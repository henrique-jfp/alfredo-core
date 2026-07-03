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

    async def send_command_to_satellite(self, device_id: str, command: str):
        if device_id in self.active_satellites:
            try:
                import json
                await self.active_satellites[device_id].send_text(json.dumps({"type": command}))
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
async def websocket_dashboard_endpoint(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Receive commands from dashboard (e.g. "START_STREAM:device_id")
            data = await websocket.receive_text()
            if data.startswith("START_STREAM:"):
                device_id = data.split(":")[1]
                await manager.send_command_to_satellite(device_id, "START_STREAM")
            elif data.startswith("STOP_STREAM:"):
                device_id = data.split(":")[1]
                await manager.send_command_to_satellite(device_id, "STOP_STREAM")
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
            "is_online": d.device_id in active_ws
        })
    return result
