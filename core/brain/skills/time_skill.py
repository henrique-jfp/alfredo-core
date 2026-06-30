from datetime import datetime
from typing import Dict, Any
from core.brain.skills.base import Skill

class TimeSkill(Skill):
    
    @property
    def name(self) -> str:
        return "TimeSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TIME"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        agora = datetime.now()
        
        # O text tem a palavra 'dia' ou 'data'?
        if "dia" in text.lower() or "data" in text.lower():
            return f"Hoje é dia {agora.day} do {agora.month} de {agora.year}."
            
        # Padrão: Horas
        hora = agora.hour
        minuto = agora.minute
        
        texto_hora = f"{hora} e {minuto}"
        if minuto == 0:
            texto_hora = f"{hora} horas"
            
        return f"Agora são {texto_hora}."
