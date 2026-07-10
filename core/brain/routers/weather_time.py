from core.brain.semantic_router import Route, _and

ROUTES = [
    # ---- TEMPO E DATA ----
    Route(r"(?=.*\bque horas sao\b)", "get_time", {"request_type": "time"}, None, False),
    Route(r"(?=.*\bque dia e hoje\b)", "get_time", {"request_type": "date"}, None, False),

    # ---- CLIMA ----
    Route(_and("como esta o|previsao do", "clima|tempo"),
          "get_weather", {"location": "current"}, None, False),
]
