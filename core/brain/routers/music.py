from core.brain.semantic_router import Route, _and, _not

ROUTES = [
    # ---- MÚSICA E MÍDIA (Spotify, especificamente) ----
    Route(_and("para|parar|pausa|pausar", "musica|som|spotify"),
          "manage_music", {"action": "pause"}, "Pausando a música.", False),

    # "toca/tocar/continua" = retomar. "volta/voltar" fica só na regra de
    # "previous" abaixo, de propósito, para não colidir com ela.
    Route(_and("toca|tocar|continua|continuar", "musica|som|spotify"),
          "manage_music", {"action": "resume"}, "Voltando a música.", False),

    Route(_and("proxima|pula|pular", "musica|som|faixa"),
          "manage_music", {"action": "next"}, "Próxima música.", False),

    Route(_and("anterior|volta|voltar", "musica|som|faixa"),
          "manage_music", {"action": "previous"}, "Música anterior.", False),
]
