from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any
from core.brain.skills.base import Skill

class TimeSkill(Skill):
    
    @property
    def name(self) -> str:
        return "TimeSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TIME"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        # Use timezone local (Brasil)
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
        
        # O text tem a palavra 'dia' ou 'data'?
        if "dia" in text.lower() or "data" in text.lower():
            if "amanhã" in text.lower() or "amanha" in text.lower():
                from datetime import timedelta
                amanha = agora + timedelta(days=1)
                return f"Amanhã será dia {amanha.day} do {amanha.month} de {amanha.year}."
            return f"Hoje é dia {agora.day} do {agora.month} de {agora.year}."
            
        # Padrão: Horas
        hora = agora.hour
        minuto = agora.minute
        
        texto_hora = f"{hora} e {minuto}"
        if minuto == 0:
            texto_hora = f"{hora} horas"
            
        return f"Agora são {texto_hora}."
