from core.brain.semantic_router import Route, _and, _not

# Palavras-chave de calendário expandidas
_CAL = (r"agenda|compromisso|compromissos|evento|eventos|calendario|calendário"
        r"|reuniao|reunião|agendado|agendada|marcado|marcada")
_ADD = "cria|criar|marca|marcar|adiciona|adicionar|novo|nova|agenda|agendar"
_REMOVE = "cancela|cancelar|remove|remover|apaga|apagar|deleta|deletar|exclui|excluir"
_RESCHEDULE = "move|mover|reagenda|reagendar|adia|adiar|empurra|empurrar|transferir|remaneja|remanejar"
_DATE = (r"hoje|amanhã|agora|semana|mês|mes|depois|próximo|próxima|próximos|próximas"
         r"|feira|segunda|terça|quarta|quinta|sexta|sábado|sabado|domingo"
         r"|fim\s*de\s*semana|final\s*de\s*semana")

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

    # READ with date keyword (inclui expressões de calendário + data)
    Route(_and(_CAL, _DATE),
          "manage_calendar", {"action": "read"}, None, False),

    # Fast Path: "o que tenho [data]" sem mencionar agenda explicitamente
    Route(r"o\s+que\s+(?:eu\s+)?tenho\s+(?:de\s+)?(?:compromisso\s+)?(.+)",
          "manage_calendar", {"action": "read"}, None, False),

    # Fast Path: "tenho reunião [data]" / "tenho compromisso [data]"
    Route(r"tenho\s+(?:alguma\s+coisa\s+)?(?:marcado|marcada|reuniao|reunião|compromisso)\s+(.+)",
          "manage_calendar", {"action": "read"}, None, False),

    # Fast Path: "próximo compromisso", "próximo evento"
    Route(r"(?:qual\s+)?(?:é\s+)?(?:o\s+)?(?:meu\s+)?(?:próximo|próxima)\s+(?:compromisso|evento)",
          "manage_calendar", {"action": "read"}, None, False),

    # Fast Path: consultas de "o que está agendado"
    Route(r"o\s+que\s+(?:está|esta|tá|ta)\s+agendado",
          "manage_calendar", {"action": "read"}, None, False),

    # Fast Path: "tenho alguma coisa marcada?"
    Route(r"tenho\s+alguma\s+coisa\s+marcada",
          "manage_calendar", {"action": "read"}, None, False),

    # READ catch-all (any mention of agenda/compromissos/reuniao)
    Route(_CAL,
          "manage_calendar", {"action": "read"}, None, False),
]
