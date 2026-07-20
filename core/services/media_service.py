import os
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger("alfredo.media_service")

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# ----------------------------------------------------------------------
# 2️⃣ MAPA DE GÊNEROS → IDs TMDB
# ----------------------------------------------------------------------
# Mapa estático de temas → IDs TMDB. Para os gêneros oficiais da TMDB,
# o ID é exato. Para temas que NÃO existem como gênero oficial (ex:
# "inspiration", "biography", "sport", "teen"), usamos o gênero oficial
# mais próximo como aproximação (comentado em cada linha) — é melhor
# devolver algo tematicamente próximo do que não devolver nada.
#
# ⚠️ Correção: no mapa anterior, "inspiration" e "romance" apontavam
# para o mesmo ID (10749, que é o ID real de Romance). Isso fazia com
# que pedidos de "filme de superação" devolvessem filmes de romance por
# engano. Agora "inspiration" usa Drama (18), a aproximação correta.
GENRE_ID_MAP: Dict[str, str] = {
    "action": "28",
    "adventure": "12",
    "animation": "16",
    "comedy": "35",
    "crime": "80",
    "documentary": "99",
    "drama": "18",
    "family": "10751",
    "fantasy": "14",
    "history": "36",
    "horror": "27",
    "inspiration": "18",          # sem gênero oficial → aproximado por Drama
    "music": "10402",
    "mystery": "9648",
    "romance": "10749",
    "science fiction": "878",
    "fiction": "878",
    "ficção científica": "878",
    "thriller": "53",
    "war": "10752",
    "western": "37",
    "biography": "18",            # sem gênero oficial → aproximado por Drama
    "sport": "18",                # sem gênero oficial → aproximado por Drama
    "teen": "18",                 # sem gênero oficial → aproximado por Drama
    "reality": "10764",           # gênero de TV (Reality); não existe para filme
}

# ----------------------------------------------------------------------
# 2b️⃣ MAPA DE TEMAS → KEYWORDS TMDB
# ----------------------------------------------------------------------
# A TMDB permite filtrar o /discover por keywords (with_keywords), que são
# muito mais precisas que gêneros para temas de vida e emoções.
#
# Enquanto o gênero "Family" (10751) devolve qualquer filme "para toda a
# família", a keyword "motherhood" (2606) devolve APENAS filmes onde a
# maternidade é um tema central. Isso resolve o problema de pedidos como
# "filme sobre maternidade" retornarem O Justiceiro ou animações genéricas.
#
# Como descobrir keyword IDs: https://www.themoviedb.org/talk/5a1030b192514162ca0015bb
# Ou use: GET https://api.themoviedb.org/3/search/keyword?query=maternidade
THEME_KEYWORD_MAP: Dict[str, List[int]] = {
    # ── maternidade / família ──────────────────────────────────
    "maternidade": [2606],                   # motherhood
    "mãe": [10861],                          # mother
    "mae": [10861],
    "mãe solteira": [202733, 2606],          # single parent + motherhood
    "mae solteira": [202733, 2606],
    "gravidez": [2661],                      # pregnancy
    "gestante": [2661],
    "paternidade": [10862],                  # father (father son relationship)
    "pai solteiro": [202733, 10862],         # single parent + father
    "filha": [2150],                         # mother daughter relationship
    "filho": [2207],                         # mother son relationship
    "família": [156293, 2150, 2207],         # family relationships + parent-child
    "familia": [156293, 2150, 2207],
    "maternal": [2606],
    "criança": [156293, 10861],              # family + mother
    "crianca": [156293, 10861],
    "amizade": [962],                        # friendship
    "amigos": [962],

    # ── romance / relacionamentos ──────────────────────────────
    "casamento": [1503],                     # wedding
    "divórcio": [2010],                      # divorce
    "divorcio": [2010],
    "traição": [9926],                       # infidelity
    "traicao": [9926],
    "lgbtqia": [2343],                       # lgbt
    "lgbt": [2343],

    # ── emoções / drama ────────────────────────────────────────
    "chorar": [10582, 1880],                 # crying + emotional
    "para chorar": [10582, 1880],
    "pra chorar": [10582, 1880],
    "luto": [155496],                        # grief
    "perda": [155496],                       # loss
    "perda de um ente querido": [155496],
    "doença": [1880],                        # illness / emotional
    "doenca": [1880],
    "câncer": [6326],                        # cancer
    "cancer": [6326],

    # ── superação / inspiração ─────────────────────────────────
    "superação": [155537],                   # overcoming / underdog
    "superacao": [155537],
    "inspiração": [155537],
    "inspiracao": [155537],
    "motivacional": [155537],
}

# Fallback: quando o gênero resolvido (ex: "family", "drama") não tem
# keyword correspondente no mapa acima, tenta estes mapeamentos genéricos.
# Isso garante que mesmo que Gemini passe "family" em vez de "maternidade",
# ainda tentamos passar keywords relevantes.
GENRE_TO_KEYWORD: Dict[str, List[int]] = {
    "family": [156293, 2606, 10861],   # family relationships + motherhood + mother
    "drama": [1880, 155496],            # emotional + grief
    "inspiration": [155537],
    "romance": [1503, 2343],            # wedding + lgbt
}

def _get_headers() -> Dict[str, str]:
    return {
        "accept": "application/json"
    }

def get_genre_id(genre_name: str, media_type: str = "movie") -> int:
    """Busca o ID do gênero correspondente na TMDB API.

    Usa o mapa estático GENRE_ID_MAP como fallback principal e,
    se não encontrar, consulta a TMDB API dinamicamente.
    """
    if not genre_name:
        return None

    name_lower = genre_name.lower().strip()

    # 1ª tentativa: mapa estático (rápido e cobre temas especiais)
    static_id = GENRE_ID_MAP.get(name_lower)
    if static_id:
        return int(static_id)

    # 2ª tentativa: consulta dinâmica na TMDB API
    if not TMDB_API_KEY:
        logger.warning("TMDB_API_KEY não configurada.")
        return None

    url = f"{BASE_URL}/genre/{media_type}/list?language=pt-BR&api_key={TMDB_API_KEY}"
    try:
        import requests as req
        res = req.get(url, headers=_get_headers(), timeout=5)
        if res.status_code == 200:
            genres = res.json().get("genres", [])
            for g in genres:
                if name_lower == g["name"].lower() or name_lower in g["name"].lower():
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

def discover_media(media_type: str = "movie", genre: str = None, year: str = None, limit: int = 3, keyword_ids: List[int] = None) -> Dict[str, Any]:
    """Busca filmes ou séries baseados nos filtros usando a TMDB API.

    Args:
        media_type: "movie" ou "tv"
        genre: Nome do gênero (ex: "action", "comedy")
        year: Ano ou década (ex: "1994" ou "1990")
        limit: Quantos resultados retornar (padrão: 3)
        keyword_ids: Lista de IDs de keywords TMDB para filtrar com precisão
                     temática (ex: [2606] para "motherhood")
    """
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

    if keyword_ids:
        # TMDB aceita múltiplos keywords separados por vírgula (OR)
        params["with_keywords"] = ",".join(str(k) for k in keyword_ids)

    url = f"{BASE_URL}/discover/{media_type}"
    
    try:
        res = requests.get(url, headers=_get_headers(), params=params, timeout=10)
        if res.status_code != 200:
            return {"error": f"Erro do TMDB: {res.status_code}"}
            
        data = res.json()
        results = data.get("results", [])
        
        if not results:
            return {"message": "Nenhum resultado encontrado para os filtros."}
            
        import random
        random.shuffle(results)
        
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
                "synopsis": overview[:150] + "..." if len(overview) > 150 else overview,
                "where_to_watch": provider_str
            })
            
        return {"results": suggestions}
    except Exception as e:
        logger.error(f"Erro na requisição TMDB: {e}")
        return {"error": "Falha de conexão com a API de Mídia."}
