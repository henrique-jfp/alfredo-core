import os
import logging
import requests
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.traffic")

class TrafficSkill(Skill):
    @property
    def name(self) -> str:
        return "TrafficSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TRAFFIC"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        # Usa o mesmo local do clima como Home
        home_lat = os.getenv("WEATHER_LAT", "-23.550520")
        home_lon = os.getenv("WEATHER_LON", "-46.633308")
        
        work_lat = os.getenv("WORK_LAT")
        work_lon = os.getenv("WORK_LON")
        
        if not work_lat or not work_lon:
            return "As coordenadas do seu trabalho não estão configuradas. Por favor, adicione as variáveis no arquivo ponto envi."
            
        try:
            logger.info("Buscando rota na API pública do OSRM...")
            # Formato OSRM: lon,lat;lon,lat
            url = f"http://router.project-osrm.org/route/v1/driving/{home_lon},{home_lat};{work_lon},{work_lat}?overview=false"
            
            headers = {
                'User-Agent': 'AlfredoHomeOS/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != "Ok" or not data.get("routes"):
                return "Não consegui traçar uma rota entre a sua casa e o trabalho no momento."
                
            route = data["routes"][0]
            distance_meters = route.get("distance", 0)
            duration_seconds = route.get("duration", 0)
            
            distance_km = round(distance_meters / 1000, 1)
            # Replace ponto por vírgula para leitura mais natural
            dist_str = str(distance_km).replace(".", ",")
            
            duration_mins = int(duration_seconds / 60)
            
            if duration_mins < 1:
                tempo = "menos de um minuto"
            elif duration_mins == 1:
                tempo = "cerca de 1 minuto"
            else:
                tempo = f"cerca de {duration_mins} minutos"
                
            return f"A distância até o trabalho é de {dist_str} quilômetros. De carro, a viagem levará {tempo}."
            
        except Exception as e:
            logger.error(f"Erro na API OSRM: {e}")
            return "Desculpe, estou sem acesso ao serviço de rotas no momento."
