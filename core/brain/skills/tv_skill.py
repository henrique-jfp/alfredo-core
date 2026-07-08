from typing import Dict, Any
from core.services.samsung_tv import SamsungTVManager

class TVSkill:
    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str:
        action = arguments.get("action")
        app_name = arguments.get("app_name")
        volume = arguments.get("volume")
        target_room = arguments.get("target_room")
        
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
        
        # Verifica o status atual antes de agir
        tv_info = tv.get_status()
        power_state = tv_info.get("device", {}).get("PowerState", "unknown")
        
        # Se a TV estiver respondendo via rede mas em standby, power_state será "standby"
        # Se ela não responder a nada, tv_info["status"] será "offline"
        is_on = power_state == "on"
        is_offline = tv_info.get("status") == "offline"
        
        if action == "power_on":
            if is_on:
                return "A TV já está ligada."
                
            # Se a TV estiver offline, o SmartThings/WOL deve acordar a TV via rede
            tv.power_on()
            
            # Se ela estiver em standby mas respondendo à rede (is_offline == False), o KEY_POWER liga a tela
            if not is_offline:
                tv.send_key("KEY_POWER")
                
            return "Ligando a TV."
            
        elif action == "power_off":
            if is_offline or power_state == "standby":
                return "A TV já está desligada."
                
            tv.send_key("KEY_POWER")
            return "Desligando a TV."
            
        elif action == "mute":
            tv.set_mute(True)
            return "A TV foi colocada no mudo."
            
        elif action == "unmute":
            tv.set_mute(False)
            return "O som da TV foi ativado."
            
        elif action == "volume_up":
            for _ in range(3):
                tv.send_key("KEY_VOLUP")
            return "Aumentando o volume da TV."
            
        elif action == "volume_down":
            for _ in range(3):
                tv.send_key("KEY_VOLDOWN")
            return "Abaixando o volume da TV."
            
        elif action == "set_volume":
            if volume and tv.set_volume(volume):
                return f"Volume da TV ajustado para {volume}."
            return "Não consegui definir o volume numérico. Isso requer a configuração do SmartThings no painel."
            
        elif action == "open_app":
            if not app_name:
                return "Qual aplicativo devo abrir?"
            
            # Map of common apps for Tizen
            apps = {
                "netflix": "11101200001",
                "youtube": "111299001912",
                "spotify": "3201606009684",
                "amazon prime": "3201512006785",
                "prime video": "3201512006785",
                "globoplay": "3201603008210",
                "disney": "3201901017640",
                "hbo": "3201807016597",
                "apple tv": "3201807016597" # verify later
            }
            app_id = apps.get(app_name.lower())
            if app_id:
                tv.open_app(app_id)
                return f"Abrindo {app_name} na TV."
            else:
                return f"Não encontrei o ID do aplicativo {app_name}."
                
        return "Comando de TV não reconhecido."
