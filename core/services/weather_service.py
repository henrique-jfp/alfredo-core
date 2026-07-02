import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from core.brain.memory import models

logger = logging.getLogger("alfredo.weather")

def get_weather_description(code: int) -> str:
    """Traduz o código WMO para uma descrição em português."""
    wmo_map = {
        0: "céu limpo",
        1: "céu predominantemente limpo",
        2: "céu parcialmente nublado",
        3: "céu nublado",
        45: "com neblina",
        48: "com neblina densa",
        51: "com garoa leve",
        53: "com garoa moderada",
        55: "com garoa densa",
        61: "com chuva leve",
        63: "com chuva moderada",
        65: "com chuva forte",
        71: "com queda de neve leve",
        80: "com pancadas de chuva leves",
        81: "com pancadas de chuva moderadas",
        82: "com pancadas de chuva violentas",
        95: "com tempestade",
        96: "com tempestade e granizo leve",
        99: "com tempestade e granizo forte"
    }
    return wmo_map.get(code, "condição desconhecida")

def get_current_weather(db: Session = None) -> dict:
    """
    Retorna o clima atual usando cache de 30 minutos.
    Se db for None (ou se não houver registro), faz requisição à API.
    """
    lat = os.getenv("WEATHER_LATITUDE", "-23.5505")
    lon = os.getenv("WEATHER_LONGITUDE", "-46.6333")
    
    if db:
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        lat = config.get("home_lat", lat)
        lon = config.get("home_lon", lon)
        
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
                "weather_code": cached.weather_code
            }

    # Sem cache válido, busca na API
    logger.info("Buscando clima atualizado na API Open-Meteo...")
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=America%2FSao_Paulo"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        current = data.get("current", {})
        temp = str(current.get("temperature_2m", "0"))
        hum = str(current.get("relative_humidity_2m", "0"))
        code = int(current.get("weather_code", -1))
        
        desc = get_weather_description(code)
        
        result = {
            "temperature": temp,
            "humidity": hum,
            "description": desc,
            "weather_code": code
        }
        
        # Salva no cache
        if db:
            new_cache = models.WeatherCache(
                latitude=lat,
                longitude=lon,
                temperature=temp,
                humidity=hum,
                weather_code=code,
                description=desc
            )
            db.add(new_cache)
            db.commit()
            
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar clima no Open-Meteo: {e}")
        # Retorna algo genérico em caso de falha completa
        return {
            "temperature": "?",
            "humidity": "?",
            "description": "indisponível",
            "weather_code": -1
        }

def get_weather_data_for_tool(db: Session, location: str, date_str: str) -> dict:
    """Busca o clima ou previsão baseado nos parâmetros do LLM."""
    # Simples geocoding ignorado por enquanto, usa a casa se não informado.
    # Em uma versão completa, usaríamos a API do Google para buscar o lat/lon do 'location'.
    lat = os.getenv("WEATHER_LATITUDE", "-23.5505")
    lon = os.getenv("WEATHER_LONGITUDE", "-46.6333")
    
    if db and not location:
        settings = db.query(models.Setting).all()
        config = {s.key: s.value for s in settings}
        lat = config.get("home_lat", lat)
        lon = config.get("home_lon", lon)

    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=America%2FSao_Paulo"
    
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        date_lower = str(date_str).lower()
        if "amanhã" in date_lower or "amanha" in date_lower:
            # Índice 1 = Amanhã
            daily = data.get("daily", {})
            return {
                "target_date": "amanhã",
                "max_temp": daily.get("temperature_2m_max", [0, 0])[1],
                "min_temp": daily.get("temperature_2m_min", [0, 0])[1],
                "description": get_weather_description(daily.get("weather_code", [0, 0])[1])
            }
        elif "depois de amanhã" in date_lower:
            daily = data.get("daily", {})
            return {
                "target_date": "depois de amanhã",
                "max_temp": daily.get("temperature_2m_max", [0, 0, 0])[2],
                "min_temp": daily.get("temperature_2m_min", [0, 0, 0])[2],
                "description": get_weather_description(daily.get("weather_code", [0, 0, 0])[2])
            }
        else:
            # Hoje (Atual)
            current = data.get("current", {})
            return {
                "target_date": "agora",
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "description": get_weather_description(current.get("weather_code", -1))
            }
    except Exception as e:
        logger.error(f"Erro no get_weather_data_for_tool: {e}")
        return {"error": "Não foi possível buscar a previsão na API externa."}
