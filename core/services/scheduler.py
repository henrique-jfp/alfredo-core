import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from core.brain.memory import models
from core.brain.memory.database import SessionLocal

logger = logging.getLogger("alfredo.scheduler")

class SchedulerManager:
    def __init__(self, get_active_connections_cb):
        self.running = False
        self.get_active_connections_cb = get_active_connections_cb

    async def start(self):
        self.running = True
        logger.info("Scheduler de background iniciado.")
        while self.running:
            try:
                await self._check_timers()
            except Exception as e:
                logger.error(f"Erro no loop do scheduler: {e}")
            await asyncio.sleep(1)

    def stop(self):
        self.running = False

    async def _check_timers(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            expired_timers = db.query(models.Timer).filter(
                models.Timer.is_active == True,
                models.Timer.expires_at <= now
            ).all()

            for timer in expired_timers:
                logger.info(f"Timer {timer.id} expirou para a sala {timer.room_id}!")
                timer.is_active = False
                
                # Procura todos os devices dessa sala para notificar
                devices = db.query(models.Device).filter(models.Device.room_id == timer.room_id).all()
                active_connections = self.get_active_connections_cb()
                
                for device in devices:
                    ws = active_connections.get(device.device_id)
                    if ws:
                        try:
                            await ws.send_json({
                                "type": "timer_expired",
                                "message": timer.message or "BIP BIP! Tempo esgotado!",
                                "duration_seconds": timer.duration_seconds
                            })
                            logger.info(f"Notificação de timer enviada ao device {device.device_id}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar aviso de timer para o device {device.device_id}: {e}")
                            
            if expired_timers:
                db.commit()
                
        finally:
            db.close()
