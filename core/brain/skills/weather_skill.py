import logging
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.services.weather_service import get_current_weather

logger = logging.getLogger("alfredo.skills")

class WeatherSkill(Skill):
    
    @property
    def name(self) -> str:
        return "WeatherSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "WEATHER"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        
        try:
            weather_data = get_current_weather(db)
            
            temp = weather_data.get("temperature", "?")
            desc = weather_data.get("description", "condição desconhecida")
            hum = weather_data.get("humidity", "?")
            
            # Formatar a string falada natural
            return f"A temperatura agora é de {temp} graus, com {desc} e {hum} por cento de umidade."
            
        except Exception as e:
            logger.error(f"Erro na execução da WeatherSkill: {e}")
            return "Desculpe, não consegui consultar a previsão do tempo no momento."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from core.services.weather_service import get_weather_data_for_tool
        db = context.get("db")
        location = kwargs.get("location")
        date_str = kwargs.get("date", "hoje")
        
        try:
            return get_weather_data_for_tool(db, location, date_str)
        except Exception as e:
            logger.error(f"Erro no execute_tool do WeatherSkill: {e}")
            return {"error": str(e)}
