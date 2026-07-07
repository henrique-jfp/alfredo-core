import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
import os
import time
from core.brain.memory import models
from core.brain.memory.database import SessionLocal
from core.brain.router import get_router
from core.voice.tts.engine import get_tts_engine

logger = logging.getLogger("alfredo.scheduler")
TZ = ZoneInfo("America/Sao_Paulo")

class SchedulerManager:
    def __init__(self, get_active_connections_cb):
        self.running = False
        self.get_active_connections_cb = get_active_connections_cb
        self._notified_events = set()

    async def start(self):
        self.running = True
        logger.info("Scheduler de background iniciado.")
        while self.running:
            try:
                await self._check_timers()
                await self._check_events()
                await self._check_routines()
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
                
                # Gera notificação
                devices = db.query(models.Device).filter(models.Device.room_id == timer.room_id).all()
                active_connections = self.get_active_connections_cb()
                
                # Se for "timer", gera o áudio TTS. Se for "alarm", o satélite cuida do som.
                tts_filename = None
                if timer.timer_type == "timer":
                    if timer.message:
                        text_to_speak = f"Com licença! O timer '{timer.message}' finalizou!"
                    else:
                        dur = timer.duration_seconds
                        if dur < 60:
                            desc = f"{dur} segundos"
                        elif dur < 3600:
                            mins = dur // 60
                            desc = f"{mins} minuto{'s' if mins > 1 else ''}"
                        else:
                            hrs = dur // 3600
                            desc = f"{hrs} hora{'s' if hrs > 1 else ''}"
                        text_to_speak = f"Com licença, o seu timer de {desc} finalizou!"
                    
                    tts_filename = f"timer_{timer.id}_{int(time.time())}.wav"
                    temp_dir = os.path.join(os.getcwd(), "tmp")
                    os.makedirs(temp_dir, exist_ok=True)
                    output_filepath = os.path.join(temp_dir, tts_filename)
                    
                    try:
                        tts_engine = get_tts_engine()
                        # Usa a voz configurada no banco se houver
                        voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
                        chosen_voice = voice_setting.value if voice_setting else "pt-BR-FranciscaNeural"
                        tts_engine.reload_voice(chosen_voice)
                        await tts_engine.synthesize_wav(text_to_speak, output_filepath)
                    except Exception as e:
                        logger.error(f"Erro ao gerar áudio do cronômetro: {e}")
                        tts_filename = None
                
                for device in devices:
                    ws = active_connections.get(device.device_id)
                    if ws:
                        try:
                            if timer.timer_type == "alarm":
                                await ws.send_json({
                                    "type": "play_alarm",
                                    "message": timer.message or "Despertador tocando!"
                                })
                            else:
                                if tts_filename:
                                    await ws.send_json({
                                        "type": "play_audio",
                                        "url": f"http://127.0.0.1:10001/api/audio/{tts_filename}"
                                    })
                                else:
                                    # Fallback
                                    await ws.send_json({
                                        "type": "timer_expired",
                                        "message": timer.message or "Tempo esgotado!",
                                        "duration_seconds": timer.duration_seconds
                                    })
                            logger.info(f"Notificação enviada ao device {device.device_id}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar aviso para o device {device.device_id}: {e}")
                            
            if expired_timers:
                db.commit()
                
        finally:
            db.close()

    async def _check_events(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(hours=1)

            upcoming_events = db.query(models.Event).filter(
                models.Event.start_time >= now,
                models.Event.start_time <= window_end
            ).order_by(models.Event.start_time.asc()).all()

            for event in upcoming_events:
                if event.id in self._notified_events:
                    continue
                self._notified_events.add(event.id)
                logger.info(f"Evento próximo: '{event.title}' às {event.start_time}")

                local_time = event.start_time.astimezone(TZ)
                hora_str = local_time.strftime("%H:%M").replace(":00", " horas")
                diff_min = int((event.start_time - now).total_seconds() / 60)

                if diff_min >= 55:
                    tempo_str = "daqui a aproximadamente 1 hora"
                elif diff_min >= 30:
                    tempo_str = f"daqui a {diff_min} minutos"
                elif diff_min >= 2:
                    tempo_str = f"daqui a {diff_min} minutos"
                else:
                    tempo_str = "agora"

                text_to_speak = f"Com licença! Você tem um compromisso {tempo_str}: {event.title}, às {hora_str}."

                devices = db.query(models.Device).filter(models.Device.room_id == event.room_id).all()
                active_connections = self.get_active_connections_cb()

                tts_filename = None
                try:
                    tts_filename = f"event_{event.id}_{int(time.time())}.wav"
                    temp_dir = os.path.join(os.getcwd(), "tmp")
                    os.makedirs(temp_dir, exist_ok=True)
                    output_filepath = os.path.join(temp_dir, tts_filename)
                    tts_engine = get_tts_engine()
                    voice_setting = db.query(models.Setting).filter(models.Setting.key == "assistant_voice").first()
                    chosen_voice = voice_setting.value if voice_setting else "pt-BR-FranciscaNeural"
                    tts_engine.reload_voice(chosen_voice)
                    await tts_engine.synthesize_wav(text_to_speak, output_filepath)
                except Exception as e:
                    logger.error(f"Erro ao gerar áudio do evento: {e}")
                    tts_filename = None

                for device in devices:
                    ws = active_connections.get(device.device_id)
                    if ws:
                        try:
                            if tts_filename:
                                await ws.send_json({
                                    "type": "play_audio",
                                    "url": f"http://127.0.0.1:10001/api/audio/{tts_filename}"
                                })
                            else:
                                await ws.send_json({
                                    "type": "event_reminder",
                                    "title": event.title,
                                    "start_time": local_time.isoformat()
                                })
                            logger.info(f"Notificação de evento enviada ao device {device.device_id}")
                        except Exception as e:
                            logger.error(f"Erro ao enviar evento para {device.device_id}: {e}")

            # Cleanup: remove IDs de eventos que já passaram há mais de 2 horas
            old_cutoff = now - timedelta(hours=2)
            old_events = db.query(models.Event).filter(
                models.Event.id.in_(self._notified_events),
                models.Event.start_time < old_cutoff
            ).all()
            for e in old_events:
                self._notified_events.discard(e.id)

        except Exception as e:
            logger.error(f"Erro no _check_events: {e}")
        finally:
            db.close()

    async def _check_routines(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now() # Usa timezone local para comparar com HH:MM do usuário
            current_time_str = now.strftime("%H:%M")
            current_day_str = now.strftime("%w") # 0=Sunday, 6=Saturday
            
            routines = db.query(models.Routine).filter(
                models.Routine.is_active == True,
                models.Routine.trigger_type == "time",
                models.Routine.trigger_value == current_time_str
            ).all()
            
            for routine in routines:
                days_list = routine.days_of_week.split(",") if routine.days_of_week else ["0","1","2","3","4","5","6"]
                if current_day_str not in days_list:
                    continue

                if routine.last_run and routine.last_run.date() == now.date():
                    continue
                    
                logger.info(f"Rotina disparada: {routine.name}")
                
                if routine.action_type == "simulate_command":
                    router = get_router()
                    context = {
                        "room_id": routine.room_id,
                        "device_id": "routine_system", 
                        "db": db,
                        "ws_tasks": []
                    }
                    
                    response_text = router.process(routine.action_value, context)
                    
                    filename = f"routine_{routine.id}_{int(time.time())}.wav"
                    temp_dir = os.path.join(os.getcwd(), "tmp")
                    os.makedirs(temp_dir, exist_ok=True)
                    output_filepath = os.path.join(temp_dir, filename)
                    
                    tts_engine = get_tts_engine()
                    await tts_engine.synthesize_wav(response_text, output_filepath)
                    
                    devices = db.query(models.Device).filter(models.Device.room_id == routine.room_id).all()
                    active_connections = self.get_active_connections_cb()
                    
                    for device in devices:
                        ws = active_connections.get(device.device_id)
                        if ws:
                            try:
                                await ws.send_json({
                                    "type": "play_audio",
                                    "url": f"http://127.0.0.1:10001/api/audio/{filename}"
                                })
                                logger.info(f"Comando de rotina enviado ao device {device.device_id}")
                                
                                # Envia as pendências WebSocket geradas pela Skill para a sala toda
                                for task in context["ws_tasks"]:
                                    await ws.send_json(task["payload"])
                                    
                            except Exception as e:
                                logger.error(f"Erro ao enviar rotina para {device.device_id}: {e}")
                                
                routine.last_run = now
                
            if routines:
                db.commit()
        except Exception as e:
            logger.error(f"Erro no _check_routines: {e}")
        finally:
            db.close()
