from core.brain.semantic_router import Route, _and, _not

_TV = "tv|televisao"
_CHANNEL_NAMES = "globo|sbt|record|band|redetv|cultura|sportv|globonews|gnt|multishow|premiere|combate"
_APPS = "netflix|youtube|spotify|prime|globoplay|disney|hbo|apple tv|claro tv\\+|claro tv|claro"

ROUTES = [
    # ---- ENERGIA ----
    Route(_and("liga|ligar", _TV),
          "manage_tv", {"action": "power_on"}, None, True),

    Route(_and("desliga|desligar|apaga|apagar", _TV),
          "manage_tv", {"action": "power_off"}, None, True),

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
