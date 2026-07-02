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
        gmaps_key = config.get("google_maps_api_key")
        
        saved_locations = db.query(models.SavedLocation).all()
        loc_dict = {loc.name.lower(): loc for loc in saved_locations}
        
        casa = loc_dict.get("casa", loc_dict.get("home", loc_dict.get("lar")))
        trabalho = loc_dict.get("trabalho", loc_dict.get("work", loc_dict.get("escritório", loc_dict.get("escritorio"))))
        
        if casa:
            home_lat = casa.latitude
            home_lon = casa.longitude
        else:
            home_lat = os.getenv("WEATHER_LAT", "-23.550520")
            home_lon = os.getenv("WEATHER_LON", "-46.633308")

        if trabalho:
            work_lat = trabalho.latitude
            work_lon = trabalho.longitude
        else:
            return "As coordenadas do seu trabalho não estão configuradas. Por favor, adicione na aba Configurações do painel com o nome 'Trabalho'."
            
        try:
            if gmaps_key:
                logger.info("Buscando rota na API do Google Maps (com Trânsito)...")
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={home_lat},{home_lon}&destinations={work_lat},{work_lon}&departure_time=now&key={gmaps_key}&language=pt-BR"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
                    element = data["rows"][0]["elements"][0]
                    dist_str = element["distance"]["text"]
                    if "duration_in_traffic" in element:
                        tempo = element["duration_in_traffic"]["text"]
                    else:
                        tempo = element["duration"]["text"]
                    return f"A distância até o trabalho é de {dist_str}. Com o trânsito atual, a viagem levará {tempo}."
                else:
                    logger.warning(f"Erro no Google Maps API, tentando fallback: {data}")
                    # Continua para o fallback OSRM abaixo
            
            # FALLBACK: OSRM
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

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Versão da ferramenta chamada pelo Cerebras AgentRouter"""
        db = context.get("db")
        if not db:
            return {"error": "Banco de dados indisponível"}
            
        origin = kwargs.get("origin")
        destination = kwargs.get("destination")
        
        from core.brain.memory import models
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        gmaps_key = config.get("google_maps_api_key")
        
        saved_locations = db.query(models.SavedLocation).all()
        loc_dict = {loc.name.lower(): loc for loc in saved_locations}
        
        # Origin (fallback pra casa se não informado ou não encontrado)
        orig_obj = loc_dict.get(origin.lower()) if origin else loc_dict.get("casa", loc_dict.get("home"))
        if orig_obj:
            orig_lat = orig_obj.latitude
            orig_lon = orig_obj.longitude
        else:
            orig_lat = os.getenv("WEATHER_LAT", "-23.550520")
            orig_lon = os.getenv("WEATHER_LON", "-46.633308")
            
        # Destination
        dest_obj = loc_dict.get(destination.lower()) if destination else None
        if dest_obj:
            dest_lat = dest_obj.latitude
            dest_lon = dest_obj.longitude
        else:
            # Em uma versão madura usaríamos API de Geocoding
            # Por enquanto exigimos que esteja salvo
            return {"error": f"O destino '{destination}' não está nas localizações salvas do usuário."}
            
        try:
            if gmaps_key:
                url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={orig_lat},{orig_lon}&destinations={dest_lat},{dest_lon}&departure_time=now&key={gmaps_key}&language=pt-BR"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
                    element = data["rows"][0]["elements"][0]
                    dist_str = element["distance"]["text"]
                    tempo = element.get("duration_in_traffic", element["duration"])["text"]
                    return {
                        "origin": origin or "casa",
                        "destination": destination,
                        "distance": dist_str,
                        "duration": tempo,
                        "provider": "google_maps"
                    }
            
            # FALLBACK OSRM
            url = f"http://router.project-osrm.org/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=false"
            headers = {'User-Agent': 'AlfredoHomeOS/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                distance_km = round(route.get("distance", 0) / 1000, 1)
                duration_mins = int(route.get("duration", 0) / 60)
                return {
                    "origin": origin or "casa",
                    "destination": destination,
                    "distance": f"{distance_km} km",
                    "duration": f"{duration_mins} minutos",
                    "provider": "osrm"
                }
            return {"error": "Nenhuma rota encontrada."}
                
        except Exception as e:
            logger.error(f"Erro no execute_tool do TrafficSkill: {e}")
            return {"error": "Falha de conexão com a API de rotas."}
