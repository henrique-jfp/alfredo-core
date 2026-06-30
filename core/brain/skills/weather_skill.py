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
