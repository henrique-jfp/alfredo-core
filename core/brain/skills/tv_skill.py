from typing import Dict, Any
from core.services.samsung_tv import SamsungTVManager
import asyncio
import concurrent.futures

def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)

class TVSkill:
    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str:
        # Suporta tanto o novo schema (actions) quanto o antigo (action único)
        actions = arguments.get("actions", [])
        if not actions and "action" in arguments:
            actions = [arguments]
            
        if not actions:
            return "Nenhuma ação fornecida para a TV."
            
        # Pega target_room do root ou do primeiro item
        target_room = arguments.get("target_room") or actions[0].get("target_room")
        
        db = context.get("db")
        room_id = context.get("room_id")
        
        if not db:
            return "Erro: banco de dados não disponível."
            
        from core.brain.memory import models
        from sqlalchemy import or_

        config = None
        
        # Se o usuário especificou um cômodo, procura por ele na descrição ou id
        if target_room:
            t_room = target_room.lower()
            if "sala" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_SALA", models.TVConfig.room_id == "sala")).first()
            elif "quarto" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_BEDROOM", models.TVConfig.room_id == "quarto")).first()
            elif "escritorio" in t_room or "escritório" in t_room:
                config = db.query(models.TVConfig).filter(or_(models.TVConfig.room_id == "ROOM_OFFICE", models.TVConfig.room_id == "escritorio")).first()
            else:
                config = db.query(models.TVConfig).filter(models.TVConfig.room_id.ilike(f"%{t_room}%")).first()

        # Se não especificou ou não achou com o nome, tenta o cômodo atual do satélite
        if not config and room_id:
            config = db.query(models.TVConfig).filter(models.TVConfig.room_id == room_id).first()
            
        # Fallback: Se não achou de nenhum jeito, pega a primeira TV que existir configurada
        if not config:
            config = db.query(models.TVConfig).filter(models.TVConfig.ip_address != None).first()

        if not config or not config.ip_address:
            return "Não encontrei nenhuma TV configurada na rede. Por favor, configure o IP da TV no painel de controle."
            
        tv = SamsungTVManager(
            ip=config.ip_address,
            mac=config.mac_address,
            smartthings_pat=config.smartthings_pat,
            smartthings_device_id=config.smartthings_device_id
        )
        
        # 1. Faz a checagem de status UMA ÚNICA VEZ antes do lote de ações
        tv_info = _run_async(tv.get_status())
        power_state = tv_info.get("device", {}).get("PowerState", "unknown")
        
        is_on = power_state == "on"
        is_offline = tv_info.get("status") == "offline"
        
        import time
        
        # 2. Processa as ações em lote
        for idx, op in enumerate(actions):
            action = op.get("action")
            app_name = op.get("app_name")
            volume = op.get("volume")
            
            if action == "power_on":
                if not is_on:
                    powered_on_absolute = _run_async(tv.power_on())
                    if not powered_on_absolute and not is_offline:
                        _run_async(tv.send_key("KEY_POWER"))
                    
                    is_on = True # Assume que ligou com sucesso
                    
                    # Se há mais comandos na fila (ex: abrir app) e a TV estava desligada, 
                    # precisamos aguardar o sistema Tizen ligar a rede WebSocket
                    if idx < len(actions) - 1:
                        time.sleep(3)
                        
            elif action == "power_off":
                if not is_offline and power_state != "standby":
                    _run_async(tv.power_off())
                    is_on = False
                    
            elif action == "mute":
                _run_async(tv.set_mute(True))
                
            elif action == "unmute":
                _run_async(tv.set_mute(False))
                
            elif action == "volume_up":
                for _ in range(3):
                    _run_async(tv.send_key("KEY_VOLUP"))
                    
            elif action == "volume_down":
                for _ in range(3):
                    _run_async(tv.send_key("KEY_VOLDOWN"))
                    
            elif action == "set_volume":
                if volume:
                    _run_async(tv.set_volume(volume))
                    
            elif action == "open_app":
                if app_name:
                    apps = {
                        "netflix": "11101200001",
                        "youtube": "111299001912",
                        "spotify": "3201606009684",
                        "amazon prime": "3201512006785",
                        "prime video": "3201512006785",
                        "globoplay": "3201603008210",
                        "disney": "3201901017640",
                        "hbo": "3201807016597",
                        "apple tv": "3201807016597"
                    }
                    app_id = apps.get(app_name.lower())
                    if app_id:
                        _run_async(tv.open_app(app_id))
                        
        return "Ok!"
