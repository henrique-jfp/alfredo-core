import re
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("alfredo.semantic_router")

# Regras de roteamento semântico ultra-rápidas (Regex / Keywords).
# Permite interceptar comandos locais em < 5ms sem depender de chamadas à API LLM.
# Ordem de prioridade importa: as primeiras regras que baterem serão executadas.

ROUTES = [
    # ---- GERENCIAMENTO DE TV ----
    (r"\b(liga|ligar)\b.*\btv\b", "manage_tv", {"action": "power_on"}, "Ligando a TV."),
    (r"\b(desliga|desligar|apaga|apagar)\b.*\btv\b", "manage_tv", {"action": "power_off"}, "Desligando a TV."),
    (r"\b(muda|mudo|silencia|silenciar)\b.*\btv\b", "manage_tv", {"action": "mute"}, "TV no mudo."),
    (r"\b(tira|tirar)\b.*\bmudo\b.*\btv\b", "manage_tv", {"action": "unmute"}, "O som da TV foi ativado."),
    (r"\b(aumenta|aumentar|sobe|subir)\b.*\b(volume|som)\b.*\btv\b", "manage_tv", {"action": "volume_up"}, "Aumentando o volume da TV."),
    (r"\b(abaixa|abaixar|diminui|diminuir)\b.*\b(volume|som)\b.*\btv\b", "manage_tv", {"action": "volume_down"}, "Abaixando o volume da TV."),
    
    # ---- MÚSICA E MÍDIA ----
    (r"\b(para|parar|pausa|pausar)\b.*\b(música|musica|som|spotify)\b", "manage_music", {"action": "pause"}, "Pausando a música."),
    (r"\b(toca|tocar|volta|voltar)\b.*\b(música|musica|som|spotify)\b", "manage_music", {"action": "resume"}, "Voltando a música."),
    (r"\b(próxima|proxima|pula|pular)\b.*\b(música|musica|som|faixa)\b", "manage_music", {"action": "next"}, "Próxima música."),
    (r"\b(anterior|volta|voltar)\b.*\b(música|musica|som|faixa)\b", "manage_music", {"action": "previous"}, "Música anterior."),
    
    # ---- TEMPO E DATA ----
    (r"\bque horas s[aã]o", "get_time", {"request_type": "time"}, None), # None = deixa a skill processar a string exata
    (r"\bque dia [ée] hoje", "get_time", {"request_type": "date"}, None),
    
    # ---- CLIMA ----
    (r"\b(como est[áa] o|previs[aã]o do) (clima|tempo)\b", "get_weather", {"location": "current"}, None),
]

class FastSemanticRouter:
    def __init__(self):
        self.compiled_routes = []
        for pattern, tool, args, resp in ROUTES:
            self.compiled_routes.append((re.compile(pattern, re.IGNORECASE), tool, args, resp))

    def match(self, text: str) -> Optional[Tuple[str, Dict[str, Any], Optional[str]]]:
        """
        Tenta fazer o match do texto com as regras regulares.
        Retorna (tool_name, tool_args, direct_response) se houver match.
        """
        text = text.strip()
        for regex, tool, args, resp in self.compiled_routes:
            if regex.search(text):
                logger.info(f"FastSemanticRouter interceptou: '{text}' -> {tool}")
                return tool, args, resp
        
        return None
