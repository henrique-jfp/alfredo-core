import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from core.brain.memory import models

logger = logging.getLogger("alfredo.weather")

# Coordenadas padrão: Rio de Janeiro (caso nada esteja configurado)
DEFAULT_LAT = "-22.9068"
DEFAULT_LON = "-43.1729"


def get_current_weather(db: Session = None) -> dict:
    """
    Retorna o clima atual usando OpenWeatherMap com cache de 30 minutos.
    Usa coordenadas do banco (home_lat/home_lon) ou da cidade configurada
    (weather_city → geolocalização). Fallback: Rio de Janeiro.
    """
    lat = os.getenv("WEATHER_LATITUDE", DEFAULT_LAT)
    lon = os.getenv("WEATHER_LONGITUDE", DEFAULT_LON)
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if db:
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        lat = config.get("home_lat", lat)
        lon = config.get("home_lon", lon)
        
        # Se não tem home_lat/home_lon, tenta resolver weather_city
        if not config.get("home_lat") and config.get("weather_city"):
            try:
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={config['weather_city']}&limit=1&appid={api_key}"
                geo_resp = requests.get(geo_url, timeout=5)
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()
                if geo_data and len(geo_data) > 0:
                    lat = str(geo_data[0]["lat"])
                    lon = str(geo_data[0]["lon"])
            except Exception as e:
                logger.warning(f"Não foi possível resolver weather_city '{config['weather_city']}': {e}")
        
        # Verifica cache
        half_hour_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
        cached = db.query(models.WeatherCache).filter(
            models.WeatherCache.latitude == lat,
            models.WeatherCache.longitude == lon,
            models.WeatherCache.timestamp >= half_hour_ago
        ).order_by(models.WeatherCache.id.desc()).first()
        
        if cached:
            logger.info("Retornando clima do cache do SQLite.")
            return {
                "temperature": cached.temperature,
                "humidity": cached.humidity,
                "description": cached.description,
                "weather_code": cached.weather_code,
                "max_temp": cached.max_temp or "—", 
                "min_temp": cached.min_temp or "—"
            }

    if not api_key:
        logger.error("OPENWEATHER_API_KEY não configurada no .env!")
        return {"temperature": "?", "humidity": "?", "description": "chave de API ausente", "weather_code": -1, "max_temp": "?", "min_temp": "?"}

    logger.info("Buscando clima atualizado na API OpenWeatherMap...")
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        temp = str(round(data["main"]["temp"]))
        hum = str(data["main"]["humidity"])
        code = data["weather"][0]["id"]
        desc = data["weather"][0]["description"].capitalize()
        
        # A API de weather (current) só retorna o max/min do momento, 
        # mas é o suficiente para não quebrar a interface
        max_temp = str(round(data["main"]["temp_max"]))
        min_temp = str(round(data["main"]["temp_min"]))
        
        result = {
            "temperature": temp,
            "humidity": hum,
            "description": desc,
            "weather_code": code,
            "max_temp": max_temp,
            "min_temp": min_temp
        }
        
        # Salva no cache
        if db:
            new_cache = models.WeatherCache(
                latitude=str(lat),
                longitude=str(lon),
                temperature=temp,
                humidity=hum,
                weather_code=code,
                description=desc,
                max_temp=max_temp,
                min_temp=min_temp
            )
            db.add(new_cache)
            db.commit()
            
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar clima no OpenWeatherMap: {e}")
        return {
            "temperature": "?",
            "humidity": "?",
            "description": "indisponível temporariamente",
            "weather_code": -1,
            "max_temp": "?",
            "min_temp": "?"
        }

def get_forecast(db: Session = None) -> dict:
    """
    Retorna a previsão estendida (5 dias / 3 horas) + dados completos do current.
    """
    lat = os.getenv("WEATHER_LATITUDE", DEFAULT_LAT)
    lon = os.getenv("WEATHER_LONGITUDE", DEFAULT_LON)
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if db:
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        lat = config.get("home_lat", lat)
        lon = config.get("home_lon", lon)
        if not config.get("home_lat") and config.get("weather_city"):
            try:
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={config['weather_city']}&limit=1&appid={api_key}"
                geo_resp = requests.get(geo_url, timeout=5)
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()
                if geo_data and len(geo_data) > 0:
                    lat = str(geo_data[0]["lat"])
                    lon = str(geo_data[0]["lon"])
            except Exception:
                pass

    if not api_key:
        return {"error": "OPENWEATHER_API_KEY não configurada"}

    try:
        current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        current_resp = requests.get(current_url, timeout=5)
        current_resp.raise_for_status()
        cur = current_resp.json()

        city_name = cur.get("name", "—")
        current = {
            "temperature": str(round(cur["main"]["temp"])),
            "feels_like": str(round(cur["main"]["feels_like"])),
            "humidity": str(cur["main"]["humidity"]),
            "pressure": str(cur["main"]["pressure"]),
            "description": cur["weather"][0]["description"].capitalize(),
            "weather_code": cur["weather"][0]["id"],
            "icon": cur["weather"][0]["icon"],
            "max_temp": str(round(cur["main"]["temp_max"])),
            "min_temp": str(round(cur["main"]["temp_min"])),
            "wind_speed": str(cur["wind"]["speed"]),
            "wind_deg": cur["wind"].get("deg", 0),
            "visibility": cur.get("visibility", 0),
            "sunrise": cur["sys"]["sunrise"],
            "sunset": cur["sys"]["sunset"],
        }

        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        fc_resp = requests.get(forecast_url, timeout=5)
        fc_resp.raise_for_status()
        fc = fc_resp.json()

        hourly = []
        daily_map = {}
        for item in fc.get("list", []):
            dt = datetime.fromtimestamp(item["dt"], tz=timezone.utc)
            entry = {
                "dt": item["dt"],
                "time": dt.strftime("%H:%M"),
                "date": dt.strftime("%Y-%m-%d"),
                "temp": round(item["main"]["temp"]),
                "feels_like": round(item["main"]["feels_like"]),
                "humidity": item["main"]["humidity"],
                "weather_code": item["weather"][0]["id"],
                "description": item["weather"][0]["description"].capitalize(),
                "icon": item["weather"][0]["icon"],
                "wind_speed": item["wind"]["speed"],
                "pop": round(item.get("pop", 0) * 100),
            }
            hourly.append(entry)

            day = dt.strftime("%Y-%m-%d")
            if day not in daily_map:
                daily_map[day] = {"temps": [], "codes": [], "descs": [], "pops": [], "humidity": [], "wind": []}
            daily_map[day]["temps"].append(entry["temp"])
            daily_map[day]["codes"].append(entry["weather_code"])
            daily_map[day]["descs"].append(entry["description"])
            daily_map[day]["pops"].append(entry["pop"])
            daily_map[day]["humidity"].append(entry["humidity"])
            daily_map[day]["wind"].append(entry["wind_speed"])

        daily = []
        for day_key, data in daily_map.items():
            daily.append({
                "date": day_key,
                "max_temp": max(data["temps"]),
                "min_temp": min(data["temps"]),
                "weather_code": max(set(data["codes"]), key=data["codes"].count),
                "description": max(set(data["descs"]), key=data["descs"].count),
                "pop": max(data["pops"]),
            })

        return {
            "city": city_name,
            "current": current,
            "hourly": hourly[:8],
            "daily": daily,
        }

    except Exception as e:
        logger.error(f"Erro no get_forecast: {e}")
        return {"error": str(e)}


def get_weather_data_for_tool(db: Session, location: str, date_str: str) -> dict:
    """Busca o clima ou previsão baseado nos parâmetros do LLM."""
    lat = os.getenv("WEATHER_LATITUDE", DEFAULT_LAT)
    lon = os.getenv("WEATHER_LONGITUDE", DEFAULT_LON)
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if not api_key:
        return {"error": "A chave da API OpenWeatherMap não está configurada no servidor."}
        
    if location:
        try:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={location}&limit=1&appid={api_key}"
            geo_resp = requests.get(geo_url, timeout=5)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            if geo_data and len(geo_data) > 0:
                lat = str(geo_data[0]["lat"])
                lon = str(geo_data[0]["lon"])
            else:
                return {"error": f"Não consegui encontrar a localização para '{location}'."}
        except Exception as e:
            logger.error(f"Erro no geocoding do OpenWeatherMap: {e}")
            return {"error": f"Erro ao buscar coordenadas para '{location}'."}
    elif db:
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        lat = config.get("home_lat", lat)
        lon = config.get("home_lon", lon)
        
        if not config.get("home_lat") and config.get("weather_city"):
            try:
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={config['weather_city']}&limit=1&appid={api_key}"
                geo_resp = requests.get(geo_url, timeout=5)
                geo_resp.raise_for_status()
                geo_data = geo_resp.json()
                if geo_data and len(geo_data) > 0:
                    lat = str(geo_data[0]["lat"])
                    lon = str(geo_data[0]["lon"])
            except Exception as e:
                logger.warning(f"Não foi possível resolver weather_city '{config['weather_city']}': {e}")

    date_lower = str(date_str).lower()
    
    # Se for agora/hoje, chama a API current
    if "amanhã" not in date_lower and "amanha" not in date_lower:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return {
                "target_date": "agora",
                "temperature": round(data["main"]["temp"]),
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"].capitalize()
            }
        except Exception as e:
            logger.error(f"Erro no get_weather_data_for_tool (current): {e}")
            return {"error": "Não foi possível buscar a previsão atual."}
            
    # Se for amanhã ou depois, chama a API de forecast de 5 dias
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # Encontra o offset em dias
        target_offset = 1 if "amanhã" in date_lower or "amanha" in date_lower else 2
        if "depois" in date_lower:
            target_offset = 2
            
        target_date_obj = datetime.now() + timedelta(days=target_offset)
        target_day_str = target_date_obj.strftime("%Y-%m-%d")
        
        # Filtra os blocos de 3 horas que caem no dia alvo
        day_forecasts = [item for item in data.get("list", []) if item.get("dt_txt", "").startswith(target_day_str)]
        
        if not day_forecasts:
            return {"error": "Previsão não disponível para esta data."}
            
        # Calcula max e min
        temps = [item["main"]["temp"] for item in day_forecasts]
        max_temp = round(max(temps))
        min_temp = round(min(temps))
        
        # Pega a descrição do horário do meio-dia ou o primeiro disponível
        midday_item = next((item for item in day_forecasts if "12:00:00" in item.get("dt_txt", "")), day_forecasts[0])
        description = midday_item["weather"][0]["description"].capitalize()
        
        return {
            "target_date": "amanhã" if target_offset == 1 else "depois de amanhã",
            "max_temp": max_temp,
            "min_temp": min_temp,
            "description": description
        }
        
    except Exception as e:
        logger.error(f"Erro no get_weather_data_for_tool (forecast): {e}")
        return {"error": "Não foi possível buscar a previsão futura na API."}
