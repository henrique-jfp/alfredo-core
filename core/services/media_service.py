import os
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("alfredo.media_service")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

def _get_headers() -> Dict[str, str]:
    return {
        "accept": "application/json"
    }

def get_genre_id(genre_name: str, media_type: str = "movie") -> int:
    """Busca o ID do gênero correspondente na TMDB API."""
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY não configurada.")
        return None
        
    url = f"{BASE_URL}/genre/{media_type}/list?language=pt-BR&api_key={TMDB_API_KEY}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=5)
        if res.status_code == 200:
            genres = res.json().get("genres", [])
            for g in genres:
                if g["name"].lower() == genre_name.lower() or genre_name.lower() in g["name"].lower():
                    return g["id"]
    except Exception as e:
        logger.error(f"Erro ao buscar gênero no TMDB: {e}")
    return None

def get_watch_providers(media_id: int, media_type: str = "movie") -> str:
    """Busca onde o filme/série está disponível para assistir no Brasil."""
    if not TMDB_API_KEY:
        return ""
        
    url = f"{BASE_URL}/{media_type}/{media_id}/watch/providers?api_key={TMDB_API_KEY}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", {})
            br_providers = results.get("BR", {})
            
            providers = []
            if "flatrate" in br_providers: # Streaming
                providers.extend([p["provider_name"] for p in br_providers["flatrate"]])
            
            if providers:
                # Remove duplicados e junta
                unique_providers = list(set(providers))
                return ", ".join(unique_providers[:3])
    except Exception as e:
        logger.error(f"Erro ao buscar providers no TMDB: {e}")
    return ""

def discover_media(media_type: str = "movie", genre: str = None, year: str = None, limit: int = 3) -> Dict[str, Any]:
    """Busca filmes ou séries baseados nos filtros usando a TMDB API."""
    if not TMDB_API_KEY:
        return {"error": "Chave da API do TMDB (TMDB_API_KEY) não configurada no servidor."}
        
    params = {
        "api_key": TMDB_API_KEY,
        "language": "pt-BR",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "page": 1,
        "watch_region": "BR"
    }
    
    if genre:
        genre_id = get_genre_id(genre, media_type)
        if genre_id:
            params["with_genres"] = genre_id
            
    if year:
        # Se for um ano específico ou década (ex: 1990)
        if media_type == "movie":
            params["primary_release_date.gte"] = f"{year}-01-01"
            params["primary_release_date.lte"] = f"{int(year)+9}-12-31" if str(year).endswith("0") else f"{year}-12-31"
        else:
            params["first_air_date.gte"] = f"{year}-01-01"
            params["first_air_date.lte"] = f"{int(year)+9}-12-31" if str(year).endswith("0") else f"{year}-12-31"

    url = f"{BASE_URL}/discover/{media_type}"
    
    try:
        res = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if res.status_code != 200:
            return {"error": f"Erro do TMDB: {res.status_code}"}
            
        data = res.json()
        results = data.get("results", [])
        
        if not results:
            return {"message": "Nenhum resultado encontrado para os filtros."}
            
        suggestions = []
        for item in results[:limit]:
            title = item.get("title") if media_type == "movie" else item.get("name")
            overview = item.get("overview", "Sem sinopse.")
            rating = item.get("vote_average", 0)
            media_id = item.get("id")
            
            providers = get_watch_providers(media_id, media_type)
            provider_str = f"Disponível em: {providers}" if providers else "Não disponível em streamings locais."
            
            suggestions.append({
                "title": title,
                "rating": round(rating, 1),
                "overview": overview[:150] + "..." if len(overview) > 150 else overview,
                "where_to_watch": provider_str
            })
            
        return {"results": suggestions}
    except Exception as e:
        logger.error(f"Erro na requisição TMDB: {e}")
        return {"error": "Falha de conexão com a API de Mídia."}
