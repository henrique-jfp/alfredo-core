import logging
import re
from typing import Dict, Any, Tuple, Optional

from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

# ----------------------------------------------------------------------
# 1️⃣ MAPA SEMÂNTICO – palavras‑chave → (media_type, genre, optional year)
# ----------------------------------------------------------------------
# Usado pelo resolve_intent() para interpretar temas que o usuário pode
# mencionar e pelo execute_tool() para traduzir nomes de gênero recebidos
# do Gemini.
SEMANTIC_MAP: Dict[str, Tuple[str, str]] = {
    # ação
    "ação": ("movie", "action"),
    "acao": ("movie", "action"),
    "ação e aventura": ("movie", "action"),
    "herói": ("movie", "action"),
    "heroi": ("movie", "action"),
    "super-herói": ("movie", "action"),
    "super heroi": ("movie", "action"),
    # aventura
    "aventura": ("movie", "adventure"),
    "exploração": ("movie", "adventure"),
    "exploracao": ("movie", "adventure"),
    # animação
    "animação": ("movie", "animation"),
    "animacao": ("movie", "animation"),
    "desenho": ("movie", "animation"),
    "cartoon": ("movie", "animation"),
    "anime": ("movie", "animation"),
    # comédia
    "comédia": ("movie", "comedy"),
    "comedia": ("movie", "comedy"),
    "engraçado": ("movie", "comedy"),
    "engracado": ("movie", "comedy"),
    "comédia romântica": ("movie", "comedy"),
    # crime / policial
    "crime": ("movie", "crime"),
    "policial": ("movie", "crime"),
    "detetive": ("movie", "crime"),
    "investigação": ("movie", "crime"),
    "investigacao": ("movie", "crime"),
    "mistério": ("movie", "crime"),
    "misterio": ("movie", "crime"),
    # documentário
    "documentário": ("tv_series", "documentary"),
    "documentario": ("tv_series", "documentary"),
    "real": ("tv_series", "documentary"),
    # drama
    "drama": ("movie", "drama"),
    "dramático": ("movie", "drama"),
    "dramatico": ("movie", "drama"),
    "emocionante": ("movie", "drama"),
    # família
    "família": ("movie", "family"),
    "familia": ("movie", "family"),
    "maternidade": ("movie", "family"),
    "mãe": ("movie", "family"),
    "mae": ("movie", "family"),
    "mãe solteira": ("movie", "family"),
    "filha": ("movie", "family"),
    "gestante": ("movie", "family"),
    "gravidez": ("movie", "family"),
    "maternal": ("movie", "family"),
    "paternidade": ("movie", "family"),
    "criança": ("movie", "family"),
    "criancas": ("movie", "family"),
    # fantasia
    "fantasia": ("movie", "fantasy"),
    "magia": ("movie", "fantasy"),
    "feiticeiro": ("movie", "fantasy"),
    "dragão": ("movie", "fantasy"),
    "dragao": ("movie", "fantasy"),
    # terror / horror
    "terror": ("movie", "horror"),
    "horror": ("movie", "horror"),
    "assustador": ("movie", "horror"),
    "medo": ("movie", "horror"),
    "suspense de terror": ("movie", "horror"),
    # superação / inspiração
    "superação": ("movie", "inspiration"),
    "superacao": ("movie", "inspiration"),
    "superar": ("movie", "inspiration"),
    "vencer": ("movie", "inspiration"),
    "triunfo": ("movie", "inspiration"),
    "resiliência": ("movie", "inspiration"),
    "resiliencia": ("movie", "inspiration"),
    "inspirar": ("movie", "inspiration"),
    "inspirador": ("movie", "inspiration"),
    # música / musical
    "musical": ("movie", "music"),
    "música": ("movie", "music"),
    "musica": ("movie", "music"),
    # romance
    "romance": ("movie", "romance"),
    "romântico": ("movie", "romance"),
    "romantico": ("movie", "romance"),
    "amor": ("movie", "romance"),
    # ficção científica
    "ficção científica": ("movie", "science fiction"),
    "ficcao cientifica": ("movie", "science fiction"),
    "ficção": ("movie", "science fiction"),
    "sci-fi": ("movie", "science fiction"),
    "espacial": ("movie", "science fiction"),
    "espaço": ("movie", "science fiction"),
    "espaco": ("movie", "science fiction"),
    "robô": ("movie", "science fiction"),
    "robo": ("movie", "science fiction"),
    "futurista": ("movie", "science fiction"),
    # thriller / suspense
    "thriller": ("movie", "thriller"),
    "suspense": ("movie", "thriller"),
    "tensão": ("movie", "thriller"),
    "tensao": ("movie", "thriller"),
    # luta / guerra / conflito
    "luta": ("movie", "war"),
    "guerra": ("movie", "war"),
    "conflito": ("movie", "war"),
    "batalha": ("movie", "war"),
    "segunda guerra": ("movie", "war"),
    "militar": ("movie", "war"),
    # faroeste / western
    "faroeste": ("movie", "western"),
    "western": ("movie", "western"),
    "cowboy": ("movie", "western"),
    "westerns": ("movie", "western"),
    # fallback genérico
    "filme": ("movie", "any"),
    "série": ("tv_series", "any"),
    "serie": ("tv_series", "any"),
    "show": ("tv_series", "any"),
}


def resolve_intent(text: str) -> Tuple[str, str, Optional[str]]:
    """
    Converte o texto do usuário em:
        (media_type, genre, year_or_none)

    - media_type → "movie" ou "tv_series"
    - genre      → nome amigável (ex: "family", "inspiration", "war", "western")
    - year       → opcional (ex.: "anos 80" → "1980", "1994" → "1994")
    """
    lowered = text.lower()

    media_type = "movie"       # padrão
    genre: Optional[str] = None
    year: Optional[str] = None

    # Procura a primeira palavra‑chave presente no mapa
    for keyword, (mt, gr) in SEMANTIC_MAP.items():
        if keyword in lowered:
            media_type = mt
            genre = gr
            break

    # Detecta década/ano se o usuário mencionou
    if any(word in lowered for word in ("anos", "ano", "decada", "de", "entre")):
        match = re.search(r"(\d{4}|\d{2})", lowered)
        if match:
            year = match.group(1)

    # Fallback genérico se nada foi reconhecido
    if genre is None:
        genre = "any"

    return media_type, genre, year


# Nota: a tradução de nome de gênero → ID TMDB é feita pelo media_service.get_genre_id()
# que mantém o GENRE_ID_MAP completo e com fallback para a API TMDB dinâmica.


# ----------------------------------------------------------------------
# #  Skill pública
# ----------------------------------------------------------------------
class MediaSkill(Skill):
    """
    Skill responsável por buscar filmes/séries no TMDB e devolver
    resposta enriquecida (título, nota, sinopse, onde assistir).
    """

    @property
    def name(self) -> str:
        return "MediaSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MEDIA"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para recomendar filmes ou séries, preciso de detalhes sobre o que você quer assistir."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a busca de mídia com os parâmetros fornecidos pelo Gemini.

        Parâmetros esperados em kwargs:
            - media_type: "movie" ou "tv"
            - genre: nome do gênero (pode ser amigável ou ID)
            - decade_or_year: ano ou década opcional
        """
        from core.services.media_service import discover_media

        media_type = kwargs.get("media_type", "movie")
        genre = kwargs.get("genre")
        year = kwargs.get("decade_or_year")

        # ── Tradução de temas → nomes de gênero TMDB ──────────────
        # Se o Gemini passou um tema como "faroeste", "luta", etc.,
        # resolve_intent() faz a conversão para "western", "war", etc.
        if genre:
            _resolved = resolve_intent(genre)
            resolved_genre = _resolved[1]  # (media_type, genre, year)
            if resolved_genre != "any":
                genre = resolved_genre

        try:
            data = discover_media(media_type=media_type, genre=genre, year=year)
            if "results" in data and data["results"]:
                lines = []
                for r in data["results"]:
                    title = r.get("title", "Título não disponível")
                    rating = r.get("rating", "N/A")
                    synopsis = (
                        r.get("synopsis")
                        or r.get("overview", "Sinopse não disponível")
                    )
                    watch = (
                        r.get("where_to_watch")
                        or r.get("streaming_platforms", "Não informado")
                    )
                    lines.append(
                        f"{title} - Nota: {rating}\n"
                        f"Sinopse: {synopsis}\n"
                        f"Onde assistir: {watch}"
                    )
                data["direct_response"] = "\n\n".join(lines)
            elif "message" in data:
                data["direct_response"] = data["message"]
            else:
                data["direct_response"] = "Nenhum resultado encontrado."

            logger.debug(
                "MediaSkill direct_response gerado: %s...",
                data["direct_response"][:200],
            )
            return data
        except Exception as e:
            logger.error("Erro no execute_tool do MediaSkill: %s", e)
            return {"error": str(e)}
