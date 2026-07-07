import os
import re
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.traffic")

class TrafficSkill(Skill):
    @property
    def name(self) -> str:
        return "TrafficSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TRAFFIC"

    def _load_config(self, db) -> Tuple[dict, dict]:
        from core.brain.memory import models
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        saved_locations = db.query(models.SavedLocation).all()
        loc_dict = {loc.name.lower(): loc for loc in saved_locations}
        return config, loc_dict

    def _resolve_location(self, loc_dict: dict, name: str) -> Optional[Tuple[str, str]]:
        """Resolve um nome de local para (lat, lon)."""
        if not name:
            return None
        name_lower = name.lower().strip()
        for key, loc in loc_dict.items():
            if name_lower == key or name_lower in key or key in name_lower:
                return (loc.latitude, loc.longitude)
        return None

    def _parse_route_text(self, text: str, loc_dict: dict, config: dict) -> Optional[str]:
        """Parseia texto de voz extraindo origem e destino, retorna resposta TTS ou None se não encontrar."""
        text_lower = text.lower()

        # Extrai destino: "para X", "até X", "pro X", "ao X"
        dest_match = re.search(r'(?:para|até|pro|pra|ao)\s+(.+?)(?:\s*$|\s+com\s+|\s+e\s+)', text_lower)
        # "a X" (preposition) - only match if not followed by more prepositions to avoid false positives
        if not dest_match:
            dest_match = re.search(r'\ba\s+(.+?)(?:\s*$|\s+com\s+|\s+e\s+)', text_lower)
        # Extrai origem: "de X", "da X", "do X"
        orig_match = re.search(r'(?:de|da|do)\s+(.+?)\s+(?:para|até|pro|pra|ao|a)', text_lower)

        dest_name = dest_match.group(1).strip() if dest_match else None
        orig_name = orig_match.group(1).strip() if orig_match else None

        # Remove artigos "o", "a", "os", "as" do início do nome
        if dest_name:
            dest_name = re.sub(r'^(?:o|a|os|as)\s+', '', dest_name).strip()
        if orig_name:
            orig_name = re.sub(r'^(?:o|a|os|as)\s+', '', orig_name).strip()

        # Se não achou "de X", origem padrão = casa
        if not orig_name:
            orig_name = "casa"

        # Se não achou destino, tenta "trabalho" como fallback
        if not dest_name:
            if "trabalho" in text_lower or "trampo" in text_lower or "serviço" in text_lower or "servico" in text_lower:
                dest_name = "trabalho"
            else:
                # Tenta achar qualquer local salvo no texto
                for loc_name in loc_dict:
                    if loc_name in text_lower and loc_name != orig_name:
                        dest_name = loc_name
                        break

        if not dest_name:
            return None

        # Resolve coordenadas
        orig_coords = self._resolve_location(loc_dict, orig_name)
        dest_coords = self._resolve_location(loc_dict, dest_name)

        if not orig_coords:
            return f"Não encontrei o local '{orig_name}' nos lugares salvos. Cadastre ele no painel de configurações."
        if not dest_coords:
            return f"Não encontrei o destino '{dest_name}' nos lugares salvos. Cadastre ele no painel de configurações."

        gmaps_key = config.get("google_maps_api_key")
        result = self._get_route(orig_coords[0], orig_coords[1], dest_coords[0], dest_coords[1], gmaps_key)

        if result.get("error"):
            return result["error"]

        return self._format_route_response(result, orig_name, dest_name)

    def _get_route(self, orig_lat: str, orig_lon: str, dest_lat: str, dest_lon: str, gmaps_key: Optional[str]) -> dict:
        """Consulta API de rotas. Retorna dict com distance, duration, provider, ou error."""
        try:
            if gmaps_key:
                logger.info("Buscando rota na API do Google Maps (com Trânsito)...")
                url = (
                    f"https://maps.googleapis.com/maps/api/distancematrix/json"
                    f"?origins={orig_lat},{orig_lon}"
                    f"&destinations={dest_lat},{dest_lon}"
                    f"&departure_time=now&key={gmaps_key}&language=pt-BR"
                )
                response = requests.get(url, timeout=5)
                data = response.json()

                if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
                    element = data["rows"][0]["elements"][0]
                    dist_str = element["distance"]["text"]

                    has_traffic = "duration_in_traffic" in element
                    duration_no_traffic = element["duration"]["text"]
                    if has_traffic:
                        duration_traffic = element["duration_in_traffic"]["text"]
                    else:
                        duration_traffic = duration_no_traffic

                    return {
                        "distance": dist_str,
                        "duration": duration_traffic,
                        "duration_no_traffic": duration_no_traffic,
                        "has_traffic": has_traffic,
                        "provider": "google_maps"
                    }

            # FALLBACK: OSRM
            logger.info("Buscando rota na API pública do OSRM (Fallback)...")
            url = f"http://router.project-osrm.org/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=false"
            headers = {'User-Agent': 'AlfredoHomeOS/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                distance_meters = route.get("distance", 0)
                duration_seconds = route.get("duration", 0)
                distance_km = round(distance_meters / 1000, 1)
                dist_str = str(distance_km).replace(".", ",")
                duration_mins = int(duration_seconds / 60)

                return {
                    "distance": f"{dist_str} km",
                    "duration": f"{duration_mins} min" if duration_mins < 60 else f"{duration_mins // 60}h{duration_mins % 60} min",
                    "has_traffic": False,
                    "provider": "osrm"
                }

            return {"error": "Não consegui traçar uma rota entre esses lugares no momento."}

        except requests.exceptions.Timeout:
            logger.error("Timeout na API de rotas")
            return {"error": "O serviço de rotas está demorando muito para responder. Tente novamente."}
        except Exception as e:
            logger.error(f"Erro na API de rotas: {e}")
            return {"error": "Desculpe, estou sem acesso ao serviço de rotas no momento."}

    def _format_route_response(self, result: dict, orig_name: str, dest_name: str) -> str:
        """Formata o resultado da rota em texto para TTS."""
        dist = result["distance"]
        duration = result["duration"]
        orig = orig_name.capitalize()
        dest = dest_name.capitalize()

        if result.get("provider") == "google_maps" and result.get("has_traffic"):
            normal = result["duration_no_traffic"]
            return (
                f"De {orig} até {dest} são {dist}. "
                f"Com o trânsito atual, a viagem vai levar {duration}. "
                f"Sem trânsito seriam {normal}."
            )
        elif result.get("provider") == "google_maps":
            return f"De {orig} até {dest} são {dist}. A viagem leva aproximadamente {duration}."
        else:
            return f"De {orig} até {dest} são {dist} de distância, cerca de {duration} de viagem (sem trânsito em tempo real)."

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        if not db:
            return "Erro: banco de dados não disponível."

        config, loc_dict = self._load_config(db)

        # Tenta extrair origem/destino do texto
        result = self._parse_route_text(text, loc_dict, config)
        if result:
            return result

        # Fallback: casa → trabalho
        casa = loc_dict.get("casa") or loc_dict.get("home")
        trabalho = loc_dict.get("trabalho") or loc_dict.get("work")
        if not casa:
            return "Você não tem um endereço de casa configurado. Adicione nos lugares salvos do painel."
        if not trabalho:
            return "Você não tem um local de trabalho configurado. Adicione nos lugares salvos do painel."

        gmaps_key = config.get("google_maps_api_key")
        route = self._get_route(casa.latitude, casa.longitude, trabalho.latitude, trabalho.longitude, gmaps_key)
        if route.get("error"):
            return route["error"]
        return self._format_route_response(route, "casa", "trabalho")

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        if not db:
            return {"error": "Banco de dados indisponível"}

        config, loc_dict = self._load_config(db)
        origin = kwargs.get("origin", "casa")
        destination = kwargs.get("destination")

        if not destination or str(destination).strip() == "":
            destination = "trabalho"

        dest_obj = loc_dict.get(destination.lower())
        if not dest_obj:
            possible = [n for n in loc_dict if destination.lower() in n or n in destination.lower()]
            if possible:
                dest_obj = loc_dict[possible[0]]
            else:
                return {"error": f"O destino '{destination}' não está nas localizações salvas. Cadastre ele no painel de configurações."}

        orig_obj = loc_dict.get(origin.lower())
        if not orig_obj:
            possible = [n for n in loc_dict if origin.lower() in n or n in origin.lower()]
            if possible:
                orig_obj = loc_dict[possible[0]]

        if orig_obj:
            orig_lat = orig_obj.latitude
            orig_lon = orig_obj.longitude
        else:
            orig_lat = os.getenv("WEATHER_LAT", "-23.550520")
            orig_lon = os.getenv("WEATHER_LON", "-46.633308")

        gmaps_key = config.get("google_maps_api_key")
        result = self._get_route(orig_lat, orig_lon, dest_obj.latitude, dest_obj.longitude, gmaps_key)

        if result.get("error"):
            return {"error": result["error"]}

        response = {
            "origin": origin,
            "destination": destination,
            "distance": result["distance"],
            "duration": result["duration"],
            "provider": result["provider"]
        }

        if result.get("has_traffic"):
            response["duration_no_traffic"] = result["duration_no_traffic"]
            response["direct_response"] = (
                f"De {origin} até {destination} são {result['distance']}. "
                f"Com o trânsito atual, a viagem vai levar {result['duration']}. "
                f"Sem trânsito seriam {result['duration_no_traffic']}."
            )
        elif result["provider"] == "google_maps":
            response["direct_response"] = (
                f"De {origin} até {destination} são {result['distance']}. "
                f"A viagem leva aproximadamente {result['duration']}."
            )
        else:
            response["direct_response"] = (
                f"De {origin} até {destination} são {result['distance']} de distância, "
                f"cerca de {result['duration']} de viagem (sem trânsito em tempo real)."
            )

        return response
