from core.brain.semantic_router import Route, _and, _not

ROUTES = [
    # ---- LISTAS ----
    # Adicionar item à lista (captura o que vem depois do "adiciona(r)")
    Route(_and("adiciona|adicionar|coloca|colocar|poe|por", "lista") + r"(?=.*\b(?:adiciona|adicionar|coloca|colocar|poe|por)\s+(?P<item_name>.*?)\s+(?:na|a)\b)",
          "manage_list", {"action": "add"}, None, True),
    
    # O que tem na lista?
    Route(_and("o que tem na|le a|ler a|mostrar a", "lista"),
          "manage_list", {"action": "read"}, None, False),

    # Limpar lista
    Route(_and("limpa|limpar|apaga|apagar|esvazia|esvaziar", "lista"),
          "manage_list", {"action": "clear"}, None, False),
]
