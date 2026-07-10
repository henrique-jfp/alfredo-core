from core.brain.semantic_router import Route, _and, _not

_CAL = "agenda|compromisso|compromissos|evento|eventos|calendario|calendário"
_ADD = "cria|criar|marca|marcar|adiciona|adicionar|novo|nova|agenda|agendar"
_REMOVE = "cancela|cancelar|remove|remover|apaga|apagar|deleta|deletar|exclui|excluir"
_RESCHEDULE = "move|mover|reagenda|reagendar|adia|adiar|empurra|empurrar|transferir|remaneja|remanejar"
_DATE = "hoje|amanhã|agora|semana|mês|mes|depois|próximo|próxima|próximos|próximas|feira|segunda|terça|quarta|quinta|sexta|sábado|sabado|domingo"

ROUTES = [
    # ADD
    Route(_and(_CAL, _ADD),
          "manage_calendar", {"action": "add"}, None, False),

    # REMOVE
    Route(_and(_CAL, _REMOVE),
          "manage_calendar", {"action": "remove"}, None, False),

    # RESCHEDULE
    Route(_and(_CAL, _RESCHEDULE),
          "manage_calendar", {"action": "reschedule"}, None, False),

    # READ with date keyword
    Route(_and(_CAL, _DATE),
          "manage_calendar", {"action": "read"}, None, False),

    # READ catch-all (any mention of agenda/compromissos)
    Route(_CAL,
          "manage_calendar", {"action": "read", "date": "hoje"}, None, True),
]
