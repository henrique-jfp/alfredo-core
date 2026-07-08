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

import webrtcvad
import asyncio
import logging
from core.brain.memory.database import SessionLocal
from core.voice.pipeline import process_audio_pipeline
import os
import json

satellite_logger = logging.getLogger("alfredo.satellite")

# Carrega o modelo Vosk globalmente para atuar como Wake Word dos satélites Web (que não rodam IA local)
global_vosk_model = None
try:
    from vosk import Model, KaldiRecognizer
    model_path = os.path.join(os.getcwd(), "core", "voice", "stt", "models", "vosk-model-small-pt-0.3")
    if os.path.exists(model_path):
        global_vosk_model = Model(model_path)
        satellite_logger.info("Modelo Vosk Global carregado com sucesso para Satélites Web.")
except Exception as e:
    satellite_logger.error(f"Erro ao carregar modelo Vosk Global: {e}")

@router.websocket("/satellite/{device_id}")
async def websocket_satellite_endpoint(websocket: WebSocket, device_id: str):
    await manager.connect_satellite(websocket, device_id)
    
    vad = webrtcvad.Vad(3) # Modo agressivo para ignorar ruído
    audio_buffer = bytearray()
    speech_buffer = bytearray()
    silence_frames = 0
    is_speaking = False
    
    # Configuracoes para PCM 16kHz 16-bit Mono
    SILENCE_THRESHOLD = 30 # ~900ms de silêncio para cortar
    FRAME_DURATION_MS = 30
    SAMPLE_RATE = 16000
    BYTES_PER_FRAME = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000) * 2) 
    
    async def handle_phrase(phrase_bytes: bytes):
        db = SessionLocal()
        try:
            device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
            room_id = device.room_id if device else "ROOM_LIVING"
            
            satellite_logger.info(f"Processando áudio captado ({len(phrase_bytes)} bytes) do {device_id}")
            
            if device_id == "dashboard-virtual-mic":
                # Filtro de Wake Word no Servidor para o Satélite Web
                if global_vosk_model:
                    rec = KaldiRecognizer(global_vosk_model, SAMPLE_RATE)
                    rec.AcceptWaveform(phrase_bytes)
                    res = json.loads(rec.Result())
                    text = res.get('text', '').lower()
                    
                    wake_variants = ["alfredo", "alfre", "fredo", "frente", "al fredo", "alfredou", "alfreu", "alfrente", "alfred", "enredo", "enredou", "enreda", "alegre"]
                    if not any(v in text for v in wake_variants):
                        satellite_logger.info(f"Ignorando áudio (sem wake word): '{text}'")
                        return
                    satellite_logger.info(f"Wake Word detectado pelo Vosk do Servidor! Frase: '{text}'")
                    try:
                        await websocket.send_text(json.dumps({"type": "WAKE_WORD_DETECTED"}))
                    except:
                        pass

                # Para o dashboard, não faz streaming de chunks, mas sim gera 1 único arquivo WAV com todo o texto
                async for tts_chunk in process_audio_pipeline(phrase_bytes, device_id, room_id, db, is_webm=False, stream_tts=False):
                    if tts_chunk:
                        await websocket.send_bytes(tts_chunk)
            else:
                async for tts_chunk in process_audio_pipeline(phrase_bytes, device_id, room_id, db, is_webm=False):
                    if tts_chunk:
                        await websocket.send_bytes(tts_chunk)
        except Exception as e:
            satellite_logger.error(f"Erro ao processar frase do {device_id}: {e}")
        finally:
            db.close()

    try:
        while True:
            data = await websocket.receive_bytes()
            await manager.broadcast_to_dashboards(data)
            
            audio_buffer.extend(data)
            
            while len(audio_buffer) >= BYTES_PER_FRAME:
                frame = bytes(audio_buffer[:BYTES_PER_FRAME])
                del audio_buffer[:BYTES_PER_FRAME]
                
                try:
                    is_speech = vad.is_speech(frame, SAMPLE_RATE)
                except:
                    is_speech = False
                    
                if is_speech:
                    is_speaking = True
                    silence_frames = 0
                    speech_buffer.extend(frame)
                else:
                    if is_speaking:
                        silence_frames += 1
                        speech_buffer.extend(frame)
                        
                        if silence_frames >= SILENCE_THRESHOLD:
                            is_speaking = False
                            silence_frames = 0
                            phrase_bytes = bytes(speech_buffer)
                            speech_buffer = bytearray()
                            
                            # Ignora ruídos rápidos (menos de 0.25s de áudio efetivo)
                            if len(phrase_bytes) > 8000:
                                asyncio.create_task(handle_phrase(phrase_bytes))
    except WebSocketDisconnect:
        if len(speech_buffer) > 8000:
            asyncio.create_task(handle_phrase(bytes(speech_buffer)))
        manager.disconnect_satellite(device_id)
    except Exception as e:
        satellite_logger.error(f"Erro no websocket do satélite: {e}")
        if len(speech_buffer) > 8000:
            asyncio.create_task(handle_phrase(bytes(speech_buffer)))
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
