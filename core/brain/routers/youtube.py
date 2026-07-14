from core.brain.semantic_router import Route, _and

ROUTES = [
    Route(_and("para|parar", "youtube|audio|video|video|musica|podcast|live"),
          "play_youtube", {"action": "stop"}, "Parando o YouTube.", False),

    Route(_and("para de tocar|para o audio|para a musica", "youtube"),
          "play_youtube", {"action": "stop"}, "Parando o YouTube.", False),
]
