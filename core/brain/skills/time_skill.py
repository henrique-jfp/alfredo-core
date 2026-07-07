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
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
        if "dia" in text.lower() or "data" in text.lower():
            if "amanhã" in text.lower() or "amanha" in text.lower():
                from datetime import timedelta
                amanha = agora + timedelta(days=1)
                return f"Amanhã será dia {amanha.day} do {amanha.month} de {amanha.year}."
            return f"Hoje é dia {agora.day} do {agora.month} de {agora.year}."
        hora = agora.hour
        minuto = agora.minute
        texto_hora = f"{hora} e {minuto}"
        if minuto == 0:
            texto_hora = f"{hora} horas"
        return f"Agora são {texto_hora}."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        agora = datetime.now(ZoneInfo("America/Sao_Paulo"))
        request_type = kwargs.get("request_type", "time")
        if request_type == "date":
            return {
                "direct_response": f"Hoje é dia {agora.day} do {agora.month} de {agora.year}.",
                "status": "success"
            }
        hora = agora.hour
        minuto = agora.minute
        texto_hora = f"{hora} horas"
        if minuto > 0:
            texto_hora = f"{hora} e {minuto}"
        return {
            "direct_response": f"Agora são {texto_hora}.",
            "status": "success"
        }
