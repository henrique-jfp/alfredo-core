import re

with open(r'C:\Projetos Pessoais\alfredo-core\core\services\scheduler.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Substituir o _check_routines interno
old_check_routines = r'''    async def _check_routines\(self\):
        db: Session = SessionLocal\(\)
        try:
            now = datetime\.now\(\)
            current_time_str = now\.strftime\("%H:%M"\)
            current_day_str = now\.strftime\("%w"\)
            
            routines = db\.query\(models\.Routine\)\.filter\(
                models\.Routine\.is_active == True,
                models\.Routine\.trigger_type == "time",
                models\.Routine\.trigger_value == current_time_str
            \)\.all\(\)
            
            for routine in routines:
                days_list = routine\.days_of_week\.split\(","\) if routine\.days_of_week else \["0","1","2","3","4","5","6"\]
                if current_day_str not in days_list:
                    continue

                if routine\.last_run and routine\.last_run\.date\(\) == now\.date\(\):
                    continue
                    
                logger\.info\(f"Rotina disparada: \{routine\.name\}"\)
                
                if routine\.action_type == "simulate_command":
                    router = get_router\(\)
                    context = \{
                        "room_id": routine\.room_id,
                        "device_id": "routine_system", 
                        "db": db,
                        "ws_tasks": \[\]
                    \}
                    
                    import asyncio
                    response_text = await asyncio\.to_thread\(router\.process, routine\.action_value, context\)
                    
                    filename = f"routine_\{routine\.id\}_\{int\(time\.time\(\)\)\}\.wav"
                    temp_dir = os\.path\.join\(os\.getcwd\(\), "tmp"\)
                    os\.makedirs\(temp_dir, exist_ok=True\)
                    output_filepath = os\.path\.join\(temp_dir, filename\)
                    
                    tts_engine = get_tts_engine\(\)
                    await tts_engine\.synthesize_wav\(response_text, output_filepath\)
                    
                    devices = db\.query\(models\.Device\)\.filter\(models\.Device\.room_id == routine\.room_id\)\.all\(\)
                    active_connections = self\.get_active_connections_cb\(\)
                    
                    device, ws = self\._get_first_connected_device\(devices, active_connections\)
                    if ws:
                        try:
                            await ws\.send_json\(\{
                                "type": "play_audio",
                                "url": f"http://127\.0\.0\.1:10001/api/audio/\{filename\}"
                            \}\)
                            logger\.info\(f"Comando de rotina enviado ao device \{device\.device_id\}"\)
                            
                            # Envia as pendências WebSocket geradas pela Skill para a sala toda
                            for task in context\["ws_tasks"\]:
                                await ws\.send_json\(task\["payload"\]\)
                                
                        except Exception as e:
                            logger\.error\(f"Erro ao enviar rotina para \{device\.device_id\}: \{e\}"\)
                                
                routine\.last_run = now
                
            if routines:
                db\.commit\(\)
        except Exception as e:
            logger\.error\(f"Erro no _check_routines: \{e\}"\)
        finally:
            db\.close\(\)'''

new_check_routines = '''    async def _check_routines(self):
        db: Session = SessionLocal()
        try:
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_day_str = now.strftime("%w")
            
            routines = db.query(models.Routine).filter(
                models.Routine.is_active == True,
                models.Routine.trigger_type == "time",
                models.Routine.trigger_value == current_time_str
            ).all()
            
            has_updates = False
            import asyncio
            for routine in routines:
                days_list = routine.days_of_week.split(",") if routine.days_of_week else ["0","1","2","3","4","5","6"]
                if current_day_str not in days_list:
                    continue

                if routine.last_run and routine.last_run.date() == now.date():
                    continue
                    
                routine.last_run = now
                has_updates = True
                
                # Despacha para execução sem travar o loop de check
                asyncio.create_task(execute_routine_now(routine.id))
                
            if has_updates:
                db.commit()
        except Exception as e:
            logger.error(f"Erro no _check_routines: {e}")
        finally:
            db.close()'''

# Substitui
content_new = content.replace(old_check_routines.replace(r'\(', '(').replace(r'\)', ')').replace(r'\{', '{').replace(r'\}', '}').replace(r'\[', '[').replace(r'\]', ']').replace(r'\.', '.'), new_check_routines)

append_code = '''

async def execute_routine_now(routine_id: int):
    from core.brain.memory.database import SessionLocal
    from core.brain.memory import models
    db = SessionLocal()
    try:
        from core.brain.router import get_router
        from core.voice.tts.engine import get_tts_engine
        import json
        import asyncio
        import time
        import os
        from core.api.satellite import manager

        routine = db.query(models.Routine).filter(models.Routine.id == routine_id).first()
        if not routine:
            return
            
        logger.info(f"Executando rotina (now): {routine.name}")
        
        context = {
            "room_id": routine.room_id,
            "device_id": "routine_system", 
            "db": db,
            "ws_tasks": []
        }
        
        response_text = ""
        
        if routine.action_type == "simulate_command":
            router = get_router()
            response_text = await asyncio.to_thread(router.process, routine.action_value, context)
            
        elif routine.action_type == "multi_action":
            try:
                actions = json.loads(routine.action_value)
                tts_parts = []
                
                for action in actions:
                    device_type = action.get("device_type")
                    if device_type in ("light", "fan"):
                        from core.brain.skills.smart_home_skill import SmartHomeSkill
                        skill = SmartHomeSkill()
                        args = {
                            "action": "turn_on" if action.get("state") == "on" else ("turn_off" if action.get("state") == "off" else action.get("speed")),
                            "device_type": device_type,
                            "target_room": action.get("location") or routine.room_id
                        }
                        if device_type == "fan":
                            if action.get("speed") == "off":
                                args["action"] = "turn_off"
                            else:
                                args["action"] = "turn_on"
                                args["speed"] = action.get("speed")
                                
                        await asyncio.to_thread(skill.execute_tool, args, context)
                        
                    elif device_type == "tv":
                        from core.brain.skills.tv_skill import TVSkill
                        skill = TVSkill()
                        args = {
                            "action": action.get("action"), 
                            "target_room": routine.room_id
                        }
                        if args["action"] == "open_app":
                            args["app_name"] = action.get("app_name")
                        await asyncio.to_thread(skill.execute_tool, args, context)
                        
                    elif device_type == "tts":
                        tts_parts.append(action.get("content", ""))
                        
                    elif device_type == "command":
                        router = get_router()
                        txt = await asyncio.to_thread(router.process, action.get("text", ""), context)
                        if txt and txt != "Ok.":
                            tts_parts.append(txt)
                            
                response_text = " ".join(tts_parts)
                if not response_text.strip():
                    response_text = ""
            except Exception as e:
                logger.error(f"Erro ao processar multi_action: {e}")
                
        if response_text or context["ws_tasks"]:
            devices = db.query(models.Device).filter(models.Device.room_id == routine.room_id).all()
            active_ids = list(manager.active_satellites.keys())
            target_ws = None
            for d in devices:
                if d.device_id in active_ids:
                    target_ws = manager.active_satellites[d.device_id]
                    break
            
            if target_ws:
                try:
                    if response_text:
                        filename = f"routine_{routine.id}_{int(time.time())}.wav"
                        temp_dir = os.path.join(os.getcwd(), "tmp")
                        os.makedirs(temp_dir, exist_ok=True)
                        output_filepath = os.path.join(temp_dir, filename)
                        
                        tts_engine = get_tts_engine()
                        await tts_engine.synthesize_wav(response_text, output_filepath)
                        
                        await target_ws.send_json({
                            "type": "play_audio",
                            "url": f"http://127.0.0.1:10001/api/audio/{filename}"
                        })
                        
                    for task in context["ws_tasks"]:
                        await target_ws.send_json(task["payload"])
                except Exception as e:
                    logger.error(f"Erro enviando wss de rotina: {e}")
    finally:
        db.close()
'''

with open(r'C:\Projetos Pessoais\alfredo-core\core\services\scheduler.py', 'w', encoding='utf-8') as f:
    if "execute_routine_now" not in content_new:
        f.write(content_new + append_code)
    else:
        f.write(content_new)
