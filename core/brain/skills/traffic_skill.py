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
        db = context.get("db")
        if not db:
            return "Erro: banco de dados não disponível."
            
        from core.brain.memory import models
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        
        home_lat = config.get("home_lat", os.getenv("WEATHER_LAT", "-23.550520"))
        home_lon = config.get("home_lon", os.getenv("WEATHER_LON", "-46.633308"))
        work_lat = config.get("work_lat")
        work_lon = config.get("work_lon")
        gmaps_key = config.get("google_maps_api_key")
        
        if not work_lat or not work_lon:
            return "As coordenadas do seu trabalho não estão configuradas. Por favor, adicione na aba Configurações do painel."
            
        try:
            if gmaps_key:
                logger.info("Buscando rota na API do Google Maps (com Trânsito)...")
                # Usa API do Google
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={home_lat},{home_lon}&destinations={work_lat},{work_lon}&departure_time=now&key={gmaps_key}&language=pt-BR"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
                    element = data["rows"][0]["elements"][0]
                    dist_str = element["distance"]["text"]
                    # Se 'duration_in_traffic' existir, usa ele. Se não, usa 'duration' normal.
                    if "duration_in_traffic" in element:
                        tempo = element["duration_in_traffic"]["text"]
                    else:
                        tempo = element["duration"]["text"]
                    return f"A distância até o trabalho é de {dist_str}. Com o trânsito atual, a viagem levará {tempo}."
                else:
                    logger.warning(f"Erro no Google Maps API: {data}")
                    return "Não consegui traçar a rota usando o Google Maps no momento."
            else:
                logger.info("Buscando rota na API pública do OSRM (Fallback)...")
                url = f"http://router.project-osrm.org/route/v1/driving/{home_lon},{home_lat};{work_lon},{work_lat}?overview=false"
                headers = {'User-Agent': 'AlfredoHomeOS/1.0'}
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") != "Ok" or not data.get("routes"):
                    return "Não consegui traçar uma rota entre a sua casa e o trabalho no momento."
                    
                route = data["routes"][0]
                distance_meters = route.get("distance", 0)
                duration_seconds = route.get("duration", 0)
                
                distance_km = round(distance_meters / 1000, 1)
                dist_str = str(distance_km).replace(".", ",")
                duration_mins = int(duration_seconds / 60)
                
                if duration_mins < 1:
                    tempo = "menos de um minuto"
                elif duration_mins == 1:
                    tempo = "cerca de 1 minuto"
                else:
                    tempo = f"cerca de {duration_mins} minutos"
                    
                return f"A distância até o trabalho é de {dist_str} quilômetros. De carro, a viagem levará {tempo} (sem estimativa em tempo real)."
                
        except Exception as e:
            logger.error(f"Erro na API de rotas: {e}")
            return "Desculpe, estou sem acesso ao serviço de rotas no momento."
