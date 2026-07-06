from typing import Dict, Any
from core.services.samsung_tv import SamsungTVManager

class TVSkill:
    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str:
        action = arguments.get("action")
        app_name = arguments.get("app_name")
        volume = arguments.get("volume")
        
        db = context.get("db")
        room_id = context.get("room_id")
        
        if not db or not room_id:
            return "Erro: banco de dados ou room_id não disponíveis."
            
        from core.brain.memory import models
        config = db.query(models.TVConfig).filter(models.TVConfig.room_id == room_id).first()
        if not config or not config.ip_address:
            return "Não encontrei nenhuma TV configurada para este cômodo. Por favor, configure o IP da TV no painel de controle."
            
        tv = SamsungTVManager(
            ip=config.ip_address,
            mac=config.mac_address,
            smartthings_pat=config.smartthings_pat,
            smartthings_device_id=config.smartthings_device_id
        )
        
        if action == "power_on":
            tv.power_on()
            tv.send_key("KEY_POWER")
            return "Ligando a TV."
            
        elif action == "power_off":
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
