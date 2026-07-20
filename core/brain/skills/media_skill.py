import logging
import re
from typing import Dict, Any, Tuple, Optional

from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

# ----------------------------------------------------------------------
# 1️⃣ MAPA SEMÂNTICO – palavras‑chave / temas / emoções → (media_type, genre)
# ----------------------------------------------------------------------
# Usado pelo resolve_intent() para interpretar temas que o usuário pode
# mencionar e pelo execute_tool() para traduzir nomes de gênero recebidos
# do Gemini.
#
# Além dos gêneros "de dicionário" (ação, comédia, terror...), este mapa
# agora cobre pedidos por TEMA DE VIDA (maternidade, luto, amizade) e por
# EMOÇÃO/EFEITO DESEJADO (chorar, rir, prender a respiração), que é como
# as pessoas normalmente pedem recomendação ("um filme pra chorar").
SEMANTIC_MAP: Dict[str, Tuple[str, str]] = {
    # ação
    "ação": ("movie", "action"),
    "acao": ("movie", "action"),
    "ação e aventura": ("movie", "action"),
    "herói": ("movie", "action"),
    "heroi": ("movie", "action"),
    "heroína": ("movie", "action"),
    "heroina": ("movie", "action"),
    "super-herói": ("movie", "action"),
    "super heroi": ("movie", "action"),
    "super-heroína": ("movie", "action"),
    "adrenalina": ("movie", "action"),
    "perseguição": ("movie", "action"),
    "perseguicao": ("movie", "action"),
    "artes marciais": ("movie", "action"),
    "explosão": ("movie", "action"),
    "explosao": ("movie", "action"),
 
    # aventura
    "aventura": ("movie", "adventure"),
    "exploração": ("movie", "adventure"),
    "exploracao": ("movie", "adventure"),
    "expedição": ("movie", "adventure"),
    "expedicao": ("movie", "adventure"),
    "jornada": ("movie", "adventure"),
    "sobrevivência": ("movie", "adventure"),
    "sobrevivencia": ("movie", "adventure"),
    "ilha deserta": ("movie", "adventure"),
    "tesouro": ("movie", "adventure"),
 
    # animação
    "animação": ("movie", "animation"),
    "animacao": ("movie", "animation"),
    "desenho": ("movie", "animation"),
    "desenho animado": ("movie", "animation"),
    "cartoon": ("movie", "animation"),
    "anime": ("movie", "animation"),
    "stop motion": ("movie", "animation"),
    "pixar": ("movie", "animation"),
 
    # comédia
    "comédia": ("movie", "comedy"),
    "comedia": ("movie", "comedy"),
    "engraçado": ("movie", "comedy"),
    "engracado": ("movie", "comedy"),
    "hilário": ("movie", "comedy"),
    "hilario": ("movie", "comedy"),
    "comédia romântica": ("movie", "comedy"),
    "comedia romantica": ("movie", "comedy"),
    "pastelão": ("movie", "comedy"),
    "pastelao": ("movie", "comedy"),
    "humor": ("movie", "comedy"),
    "sátira": ("movie", "comedy"),
    "satira": ("movie", "comedy"),
    "paródia": ("movie", "comedy"),
    "parodia": ("movie", "comedy"),
    "comédia de humor negro": ("movie", "comedy"),
    "humor negro": ("movie", "comedy"),
    "leve": ("movie", "comedy"),
    "descontraído": ("movie", "comedy"),
    "descontraido": ("movie", "comedy"),
    "pipoca": ("movie", "comedy"),
    "para rir": ("movie", "comedy"),
    "pra rir": ("movie", "comedy"),
    "rir": ("movie", "comedy"),
    "rir muito": ("movie", "comedy"),
 
    # crime / policial
    "crime": ("movie", "crime"),
    "policial": ("movie", "crime"),
    "detetive": ("movie", "mystery"),
    "investigação": ("movie", "crime"),
    "investigacao": ("movie", "crime"),
    "gângster": ("movie", "crime"),
    "gangster": ("movie", "crime"),
    "máfia": ("movie", "crime"),
    "mafia": ("movie", "crime"),
    "roubo": ("movie", "crime"),
    "assalto": ("movie", "crime"),
    "golpe": ("movie", "crime"),
    "crime organizado": ("movie", "crime"),
    "true crime": ("tv_series", "documentary"),
    "crime real": ("tv_series", "documentary"),
    "serial killer": ("movie", "crime"),
    "assassino em série": ("movie", "crime"),
    "assassino em serie": ("movie", "crime"),
 
    # mistério (separado de crime, é gênero oficial na TMDB)
    "mistério": ("movie", "mystery"),
    "misterio": ("movie", "mystery"),
    "enigma": ("movie", "mystery"),
    "quem matou": ("movie", "mystery"),
    "sobrenatural investigativo": ("movie", "mystery"),
    "suspense de mistério": ("movie", "mystery"),
 
    # documentário
    "documentário": ("tv_series", "documentary"),
    "documentario": ("tv_series", "documentary"),
    "docsérie": ("tv_series", "documentary"),
    "docserie": ("tv_series", "documentary"),
    "docfilme": ("movie", "documentary"),
    "documentário em filme": ("movie", "documentary"),
    "documentario em filme": ("movie", "documentary"),
    "real": ("tv_series", "documentary"),
    "baseado em fatos reais": ("movie", "documentary"),
    "história real": ("movie", "documentary"),
    "historia real": ("movie", "documentary"),
 
    # drama
    "drama": ("movie", "drama"),
    "dramático": ("movie", "drama"),
    "dramatico": ("movie", "drama"),
    "emocionante": ("movie", "drama"),
    "comovente": ("movie", "drama"),
    "tocante": ("movie", "drama"),
    "sensível": ("movie", "drama"),
    "sensivel": ("movie", "drama"),
    "profundo": ("movie", "drama"),
    "reflexivo": ("movie", "drama"),
    "que faz pensar": ("movie", "drama"),
    "nostalgia": ("movie", "drama"),
    "nostálgico": ("movie", "drama"),
    "nostalgico": ("movie", "drama"),
    "final triste": ("movie", "drama"),
    "final marcante": ("movie", "drama"),
    "luto": ("movie", "drama"),
    "perda": ("movie", "drama"),
    "perda de um ente querido": ("movie", "drama"),
    "doença": ("movie", "drama"),
    "doenca": ("movie", "drama"),
    "câncer": ("movie", "drama"),
    "cancer": ("movie", "drama"),
    "traição": ("movie", "drama"),
    "traicao": ("movie", "drama"),
    # pedidos de EMOÇÃO/EFEITO desejado (muito comuns na fala do usuário)
    "chorar": ("movie", "drama"),
    "para chorar": ("movie", "drama"),
    "pra chorar": ("movie", "drama"),
    "chorar litros": ("movie", "drama"),
    "chorar muito": ("movie", "drama"),
    "me emocionar": ("movie", "drama"),
    "emocionar": ("movie", "drama"),
    "arrancar lágrimas": ("movie", "drama"),
    "arrancar lagrimas": ("movie", "drama"),
 
    # família
    "família": ("movie", "family"),
    "familia": ("movie", "family"),
    "maternidade": ("movie", "family"),
    "mãe": ("movie", "family"),
    "mae": ("movie", "family"),
    "mãe solteira": ("movie", "family"),
    "mae solteira": ("movie", "family"),
    "pai solteiro": ("movie", "family"),
    "paternidade": ("movie", "family"),
    "filha": ("movie", "family"),
    "filho": ("movie", "family"),
    "gestante": ("movie", "family"),
    "gravidez": ("movie", "family"),
    "maternal": ("movie", "family"),
    "criança": ("movie", "family"),
    "crianca": ("movie", "family"),
    "criancas": ("movie", "family"),
    "infantil": ("movie", "family"),
    "para a família toda": ("movie", "family"),
    "pra assistir com os filhos": ("movie", "family"),
    "amizade": ("movie", "family"),
    "amigos": ("movie", "family"),
 
    # fantasia
    "fantasia": ("movie", "fantasy"),
    "magia": ("movie", "fantasy"),
    "mágico": ("movie", "fantasy"),
    "magico": ("movie", "fantasy"),
    "feiticeiro": ("movie", "fantasy"),
    "feiticeira": ("movie", "fantasy"),
    "bruxa": ("movie", "fantasy"),
    "bruxo": ("movie", "fantasy"),
    "dragão": ("movie", "fantasy"),
    "dragao": ("movie", "fantasy"),
    "conto de fadas": ("movie", "fantasy"),
    "mundo mágico": ("movie", "fantasy"),
    "mundo magico": ("movie", "fantasy"),
 
    # terror / horror
    "terror": ("movie", "horror"),
    "horror": ("movie", "horror"),
    "assustador": ("movie", "horror"),
    "medo": ("movie", "horror"),
    "suspense de terror": ("movie", "horror"),
    "sobrenatural": ("movie", "horror"),
    "vampiro": ("movie", "horror"),
    "zumbi": ("movie", "horror"),
    "fantasma": ("movie", "horror"),
    "possessão": ("movie", "horror"),
    "possessao": ("movie", "horror"),
    "slasher": ("movie", "horror"),
    "casa assombrada": ("movie", "horror"),
    "me apavorar": ("movie", "horror"),
    "passar medo": ("movie", "horror"),
 
    # superação / inspiração
    "superação": ("movie", "inspiration"),
    "superacao": ("movie", "inspiration"),
    "superar": ("movie", "inspiration"),
    "superar desafios": ("movie", "inspiration"),
    "vencer": ("movie", "inspiration"),
    "vencer na vida": ("movie", "inspiration"),
    "triunfo": ("movie", "inspiration"),
    "resiliência": ("movie", "inspiration"),
    "resiliencia": ("movie", "inspiration"),
    "inspirar": ("movie", "inspiration"),
    "inspirador": ("movie", "inspiration"),
    "motivacional": ("movie", "inspiration"),
    "força de vontade": ("movie", "inspiration"),
    "forca de vontade": ("movie", "inspiration"),
    "recomeço": ("movie", "inspiration"),
    "recomeco": ("movie", "inspiration"),
    "segunda chance": ("movie", "inspiration"),
    "virada de jogo": ("movie", "inspiration"),
    "conquista": ("movie", "inspiration"),
    "contra todas as chances": ("movie", "inspiration"),
    "história inspiradora": ("movie", "inspiration"),
    "historia inspiradora": ("movie", "inspiration"),
 
    # música / musical
    "musical": ("movie", "music"),
    "música": ("movie", "music"),
    "musica": ("movie", "music"),
    "banda": ("movie", "music"),
    "cantor": ("movie", "music"),
    "cantora": ("movie", "music"),
    "show de música": ("movie", "music"),
 
    # romance
    "romance": ("movie", "romance"),
    "romântico": ("movie", "romance"),
    "romantico": ("movie", "romance"),
    "amor": ("movie", "romance"),
    "paixão": ("movie", "romance"),
    "paixao": ("movie", "romance"),
    "casal": ("movie", "romance"),
    "casamento": ("movie", "romance"),
    "divórcio": ("movie", "romance"),
    "divorcio": ("movie", "romance"),
    "primeiro amor": ("movie", "romance"),
    "amor proibido": ("movie", "romance"),
    "triângulo amoroso": ("movie", "romance"),
    "triangulo amoroso": ("movie", "romance"),
    "lgbtqia": ("movie", "romance"),
    "lgbt": ("movie", "romance"),
 
    # ficção científica
    "ficção científica": ("movie", "science fiction"),
    "ficcao cientifica": ("movie", "science fiction"),
    "ficção": ("movie", "science fiction"),
    "ficcao": ("movie", "science fiction"),
    "sci-fi": ("movie", "science fiction"),
    "scifi": ("movie", "science fiction"),
    "espacial": ("movie", "science fiction"),
    "espaço": ("movie", "science fiction"),
    "espaco": ("movie", "science fiction"),
    "robô": ("movie", "science fiction"),
    "robo": ("movie", "science fiction"),
    "futurista": ("movie", "science fiction"),
    "alienígena": ("movie", "science fiction"),
    "alienigena": ("movie", "science fiction"),
    "distopia": ("movie", "science fiction"),
    "viagem no tempo": ("movie", "science fiction"),
    "inteligência artificial": ("movie", "science fiction"),
    "inteligencia artificial": ("movie", "science fiction"),
 
    # thriller / suspense
    "thriller": ("movie", "thriller"),
    "suspense": ("movie", "thriller"),
    "tensão": ("movie", "thriller"),
    "tensao": ("movie", "thriller"),
    "espionagem": ("movie", "thriller"),
    "prender a respiração": ("movie", "thriller"),
    "prender a respiracao": ("movie", "thriller"),
    "psicológico": ("movie", "thriller"),
    "psicologico": ("movie", "thriller"),
    "vingança": ("movie", "thriller"),
    "vinganca": ("movie", "thriller"),
 
    # luta / guerra / conflito
    "luta": ("movie", "war"),
    "guerra": ("movie", "war"),
    "conflito": ("movie", "war"),
    "batalha": ("movie", "war"),
    "segunda guerra": ("movie", "war"),
    "guerra fria": ("movie", "war"),
    "militar": ("movie", "war"),
 
    # faroeste / western
    "faroeste": ("movie", "western"),
    "western": ("movie", "western"),
    "cowboy": ("movie", "western"),
    "westerns": ("movie", "western"),
    "velho oeste": ("movie", "western"),
 
    # biografia
    "biografia": ("movie", "biography"),
    "biopic": ("movie", "biography"),
    "vida real": ("movie", "biography"),
    "história de vida": ("movie", "biography"),
    "historia de vida": ("movie", "biography"),
 
    # esporte
    "esporte": ("movie", "sport"),
    "esportivo": ("movie", "sport"),
    "atleta": ("movie", "sport"),
    "competição esportiva": ("movie", "sport"),
    "futebol": ("movie", "sport"),
    "olimpíadas": ("movie", "sport"),
    "olimpiadas": ("movie", "sport"),
 
    # adolescente / coming of age
    "adolescente": ("tv_series", "teen"),
    "teen": ("tv_series", "teen"),
    "colégio": ("tv_series", "teen"),
    "colegio": ("tv_series", "teen"),
    "ensino médio": ("tv_series", "teen"),
    "ensino medio": ("tv_series", "teen"),
    "coming of age": ("movie", "teen"),
    "amadurecimento": ("movie", "teen"),
    "autoconhecimento": ("movie", "teen"),
    "identidade": ("movie", "teen"),
 
    # reality show
    "reality show": ("tv_series", "reality"),
    "reality": ("tv_series", "reality"),
 
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
