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
            data = get_weather_data_for_tool(db, location, date_str)
            if "error" in data:
                data["direct_response"] = data["error"]
                return data
            data["direct_response"] = self._format_direct(data)
            return data
        except Exception as e:
            logger.error(f"Erro no execute_tool do WeatherSkill: {e}")
            return {"error": str(e), "direct_response": "Desculpe, não consegui obter essa informação do tempo no momento."}
    
    def _format_direct(self, data: dict) -> str:
        date = data.get("target_date", "agora")
        desc = data.get("description", "sem informação")
        if date == "agora":
            temp = data.get("temperature", "?")
            hum = data.get("humidity", "?")
            return f"A temperatura {date} é de {temp} graus, com {desc} e {hum} por cento de umidade."
        else:
            max_t = data.get("max_temp", "?")
            min_t = data.get("min_temp", "?")
            return f"A previsão para {date} é {desc}, com máxima de {max_t} e mínima de {min_t} graus."
