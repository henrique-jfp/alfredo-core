import re
from core.brain.semantic_router import Route, _and, _not

_TV = "tv|televisao"
_CHANNEL_NAMES = "globo|sbt|record|band|redetv|cultura|sportv|globonews|gnt|multishow|premiere|combate"
_APPS = "netflix|youtube|spotify|prime|globoplay|disney|hbo|apple tv|claro tv\\+|claro tv|claro"

# ── Extração de cômodo para comandos de TV ──────────────────────────────
# Resolve "da sala", "do quarto", "do escritório" etc. O mesmo padrão
# usado em smart_home.py, mantido aqui para independência do módulo.

_ROOM_MAP = [
    (["sala de jantar", "sala jantar"], "sala de jantar"),
    (["sala de estar"], "sala de estar"),
    (["sala"], "sala"),
    (["quarto da laura", "quarto laura"], "quarto da laura"),
    (["quarto do casal", "quarto casal", "meu quarto"], "quarto do casal"),
    (["quarto"], "quarto"),
    (["escritorio", "escritório"], "escritorio"),
    (["cozinha"], "cozinha"),
    (["varanda", "sacada"], "varanda"),
    (["banheiro", "wc"], "banheiro"),
]


def _extract_room(text: str) -> str | None:
    """Extrai o nome do cômodo do texto normalizado."""
    for phrases, room_name in _ROOM_MAP:
        for phrase in phrases:
            if re.search(rf"\b{re.escape(phrase)}\b", text):
                return room_name
    return None


def _has_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _has_any(text: str, words: str) -> bool:
    """words é uma pipe-separated string de alternativas."""
    return re.search(rf"\b(?:{words})\b", text) is not None


def _parse_tv_power(text: str) -> list[dict] | None:
    """
    Custom parser para comandos de energia da TV (ligar/desligar).
    Extrai o cômodo opcional ('da sala', 'do quarto') e o inclui
    nos argumentos como 'target_room'.

    Retorna lista com 1 dict de ação, ou None se não for comando de energia.
    """
    # Verifica se menciona TV
    if not _has_any(text, _TV):
        return None

    action = None
    if _has_any(text, "liga|ligar|acende|acender"):
        action = "power_on"
    elif _has_any(text, "desliga|desligar|apaga|apagar|apague"):
        action = "power_off"

    if not action:
        return None

    args = {"action": action}

    # Extrai cômodo se mencionado
    room = _extract_room(text)
    if room:
        args["target_room"] = room

    return [args]


ROUTES = [
    # ---- ENERGIA (com extração de cômodo) ----
    Route(
        r".*",  # pattern genérico — o custom_parser decide
        "manage_tv",
        {},
        None,
        True,
        custom_parser=_parse_tv_power,
    ),

    # ---- MUDO ----
    Route(rf"(?:{_and(_TV, 'mudo', 'tira|tirar')})|(?:{_and(_TV, 'desmuta|desmutar')})",
          "manage_tv", {"action": "unmute"}, None, True),

    Route(_and(_TV, "silencia|silenciar|muta|mutar|mudo") + _not("tira|tirar|desmuta|desmutar"),
          "manage_tv", {"action": "mute"}, None, True),

    # ---- VOLUME ----
    # "coloca o volume no 30", "ajusta o volume pra 50", "muda o volume"
    Route(_and("coloca|colocar|ajusta|ajustar|deixa|deixar|poe|por|muda|mudar", "volume")
          + r"(?=.*\b(?P<level>\d{1,3})\b)",
          "manage_tv", {"action": "volume_set"}, None, True),

    # "volume no 30", "volume 30" (sem verbo — fallback para qdo o Gemini não pega)
    Route(r"(?=.*\bvolume\b)" + r"(?=.*\b(?P<level>\d{1,3})\b)",
          "manage_tv", {"action": "volume_set"}, None, True),

    Route(_and("aumenta|aumentar|sobe|subir", "volume|som"),
          "manage_tv", {"action": "volume_up"}, None, True),

    Route(_and("abaixa|abaixar|diminui|diminuir", "volume|som"),
          "manage_tv", {"action": "volume_down"}, None, True),

    # ---- ENTRADA / FONTE ----
    Route(r"(?=.*\b(?:muda|mudar|troca|trocar|coloca|colocar|vai|ir)\b)"
          r"(?=.*\b(?P<source>hdmi\s?[123])\b)",
          "manage_tv", {"action": "select_source"}, None, True),

    Route(_and("entrada|fonte", r"(?P<source>av|antena|tv aberta)"),
          "manage_tv", {"action": "select_source"}, None, True),

    # ---- CANAL ----
    Route(_and("muda|mudar|troca|trocar|coloca|colocar|vai|ir", "canal")
          + r"(?=.*\b(?P<channel>\d{1,4})\b)" + _not("claro"),
          "manage_tv", {"action": "channel_number"}, None, True),

    Route(_and("muda|mudar|troca|trocar|coloca|colocar|vai|ir", "canal")
          + rf"(?=.*\b(?P<channel_name>{_CHANNEL_NAMES})\b)" + _not("claro"),
          "manage_tv", {"action": "channel_name"}, None, True),

    # ---- CANAL DENTRO DE APP ----
    Route(r"(?=.*\bclaro\b)" + _and("canal") + r"(?=.*\b(?P<channel>\d{1,4})\b)",
          "manage_tv", {"action": "app_channel_change", "app_name": "claro tv+"}, None, True),

    Route(r"(?=.*\bclaro\b)" + _and("canal") + rf"(?=.*\b(?P<channel_name>{_CHANNEL_NAMES})\b)",
          "manage_tv", {"action": "app_channel_change", "app_name": "claro tv+"}, None, True),

    # ---- ABRIR APP ----
    Route(r"(?=.*\b(?:abre|abri|abrir|coloca|colocar)\b)"
          rf"(?=.*\b(?P<app_name>{_APPS})\b)" + _not("canal"),
          "manage_tv", {"action": "open_app"}, None, True),

    # ---- REPRODUÇÃO ----
    Route(r"(?=.*\b(?:play|toca|tocar|reproduz|reproduzir)\b)"
          rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
          "manage_tv", {"action": "media_play"}, None, True),

    Route(r"(?=.*\b(?:pausa|pausar)\b)"
          rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
          "manage_tv", {"action": "media_pause"}, None, True),

    Route(r"(?=.*\b(?:encerra|encerrar|sai|sair)\b)"
          rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
          "manage_tv", {"action": "media_stop"}, None, True),

    Route(_and("proximo|proxima|avanca|avancar|pula|pular", "video|filme|serie|programa|episodio"),
          "manage_tv", {"action": "media_next"}, None, True),

    Route(_and("anterior|volta|voltar", "video|filme|serie|programa|episodio"),
          "manage_tv", {"action": "media_previous"}, None, True),
]
