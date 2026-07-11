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

_global_scheduler = None

def wakeup_scheduler():
    if _global_scheduler:
        _global_scheduler.wakeup_event.set()

class SchedulerManager:
    def __init__(self, get_active_connections_cb):
        self.running = False
        self.get_active_connections_cb = get_active_connections_cb
        self._notified_events = set()
        self.wakeup_event = asyncio.Event()
        global _global_scheduler
        _global_scheduler = self

    async def _sync_next_timestamps(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            # Próximo timer ativo
            next_timer = db.query(models.Timer).filter(models.Timer.is_active == True).order_by(models.Timer.expires_at.asc()).first()
            
            # Próximo evento não notificado completamente
            window_end = now + timedelta(days=365) # Procura no horizonte longo
            upcoming_events = db.query(models.Event).filter(
                models.Event.start_time >= now,
                models.Event.start_time <= window_end
            ).all()
            
            next_event_wakeup = None
            for e in upcoming_events:
                reminders_str = e.reminders or "60"
                notified_str = e.notified or ""
                
                reminders_list = [int(r.strip()) for r in reminders_str.split(",") if r.strip().isdigit()]
                notified_list = [int(n.strip()) for n in notified_str.split(",") if n.strip().isdigit()]
                
                for r in reminders_list:
                    if r not in notified_list:
                        wake_time = e.start_time.replace(tzinfo=timezone.utc) - timedelta(minutes=r)
                        if next_event_wakeup is None or wake_time < next_event_wakeup:
                            next_event_wakeup = wake_time
            
            # Tem rotinas ativas baseadas em horário?
            has_routines = db.query(models.Routine).filter(
                models.Routine.is_active == True, 
                models.Routine.trigger_type == "time"
            ).first() is not None
            
            return next_timer, next_event_wakeup, has_routines
        finally:
            db.close()

    async def start(self):
        self.running = True
        self._last_google_sync = datetime.now(timezone.utc)
        logger.info("Scheduler Event-Driven iniciado.")
        while self.running:
            self.wakeup_event.clear()
            try:
                await self._check_timers()
                await self._check_events()
                await self._check_routines()
                await self._check_google_sync()

                next_timer, next_event, has_routines = await self._sync_next_timestamps()

                now = datetime.now(timezone.utc)
                sleep_times = [900]

                if next_timer:
                    delta = (next_timer.expires_at - now).total_seconds()
                    sleep_times.append(max(0, delta))

                if next_event:
                    delta = (next_event - now).total_seconds()
                    sleep_times.append(max(0, delta))

                if has_routines:
                    now_local = datetime.now()
                    sec_to_next_minute = 60 - now_local.second
                    sleep_times.append(max(0, sec_to_next_minute))

                timeout = min(sleep_times)
                if timeout <= 0:
                    timeout = 1

                try:
                    await asyncio.wait_for(self.wakeup_event.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    pass

            except Exception as e:
                logger.error(f"Erro no loop do scheduler: {e}")
                await asyncio.sleep(5)

    def stop(self):
        self.running = False
        self.wakeup_event.set()

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

                # Sempre envia para o dashboard se estiver aberto
                ws_dash = active_connections.get("dashboard-virtual-mic")
                if ws_dash:
                    try:
                        if timer.timer_type == "alarm":
                            await ws_dash.send_json({
                                "type": "play_alarm",
                                "message": timer.message or "Despertador tocando!"
                            })
                        elif tts_filename:
                            await ws_dash.send_json({
                                "type": "play_audio",
                                "url": f"/api/audio/{tts_filename}"
                            })
                    except Exception as e:
                        logger.error(f"Erro ao notificar dashboard: {e}")
                            
            if expired_timers:
                db.commit()
                
        finally:
            db.close()

    @staticmethod
    def _format_reminder_time(minutes: int) -> str:
        if minutes >= 43200:
            days = minutes // 1440
            return f"em {days} dias"
        if minutes >= 1440:
            return "amanhã"
        if minutes >= 2880:
            return f"em {minutes // 1440} dias"
        if minutes == 60:
            return "em 1 hora"
        if minutes == 30:
            return "em 30 minutos"
        if minutes == 15:
            return "em 15 minutos"
        if minutes == 5:
            return "em 5 minutos, está quase na hora"
        if minutes <= 1:
            return "agora"
        return f"em {minutes} minutos"

    async def _check_events(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(hours=24)
            now_naive = now.replace(tzinfo=None)
            window_end_naive = window_end.replace(tzinfo=None)

            upcoming_events = db.query(models.Event).filter(
                models.Event.start_time >= now_naive,
                models.Event.start_time <= window_end_naive
            ).order_by(models.Event.start_time.asc()).all()

            for event in upcoming_events:
                reminders_str = event.reminders or "60"
                notified_str = event.notified or ""

                reminders_list = sorted(
                    [int(r.strip()) for r in reminders_str.split(",") if r.strip().isdigit()],
                    reverse=True
                )
                notified_list = [int(n.strip()) for n in notified_str.split(",") if n.strip().isdigit()]

                local_time = event.start_time.replace(tzinfo=timezone.utc).astimezone(TZ)
                hora_str = local_time.strftime("%H:%M").replace(":00", " horas")
                any_notified = False

                for r in reminders_list:
                    if r in notified_list:
                        any_notified = True
                        continue

                    reminder_time = event.start_time.replace(tzinfo=timezone.utc) - timedelta(minutes=r)
                    if now < reminder_time:
                        continue

                    tempo_str = self._format_reminder_time(r)
                    text_to_speak = f"Com licença! Você tem um compromisso {tempo_str}: {event.title}, às {hora_str}."

                    logger.info(f"Evento '{event.title}': lembrando {r} min antes (notified: {notified_str})")

                    devices = db.query(models.Device).filter(models.Device.room_id == event.room_id).all()
                    active_connections = self.get_active_connections_cb()

                    tts_filename = None
                    try:
                        tts_filename = f"event_{event.id}_{r}_{int(time.time())}.wav"
                        temp_dir = os.path.join(os.getcwd(), "tmp")
                        os.makedirs(temp_dir, exist_ok=True)
                        output_filepath = os.path.join(temp_dir, tts_filename)
                        tts_engine = get_tts_engine()
                        voice_setting = db.query(models.Setting).filter(
                            models.Setting.key == "assistant_voice"
                        ).first()
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

                    notified_list.append(r)
                    event.notified = ",".join(str(n) for n in sorted(notified_list))
                    db.commit()
                    any_notified = True

                self._notified_events.discard(event.id)

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
                    
                    import asyncio
                    response_text = await asyncio.to_thread(router.process, routine.action_value, context)
                    
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

    async def _check_google_sync(self):
        now = datetime.now(timezone.utc)
        delta = (now - self._last_google_sync).total_seconds()
        if delta < 300:
            return
        self._last_google_sync = now

        db: Session = SessionLocal()
        try:
            from core.services.google_calendar import sync_all, get_sync_status
            status = get_sync_status(db)
            if status["is_connected"] and status["pending_events"] > 0:
                result = sync_all(db)
                logger.info(f"Google Calendar sync automático: pushed={result['pushed']}, pulled={result['pulled']}")
        except Exception as e:
            logger.error(f"Erro no _check_google_sync: {e}")
        finally:
            db.close()
