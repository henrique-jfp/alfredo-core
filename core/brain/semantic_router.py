import re
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("alfredo.semantic_router")

# Regras de roteamento semântico ultra-rápidas (Regex / Keywords).
# Permite interceptar comandos locais em < 5ms sem depender de chamadas à API LLM.
# Ordem de prioridade importa: as primeiras regras que baterem serão executadas.

ROUTES = [
    # ---- GERENCIAMENTO DE TV (Agora suporta multi-comandos na mesma frase) ----
    (r"\b(liga|ligar)\b.*\b(tv|televisão|televisao)\b", "manage_tv", {"action": "power_on"}, "Ok!"),
    (r"\b(desliga|desligar|apaga|apagar)\b.*\b(tv|televisão|televisao)\b", "manage_tv", {"action": "power_off"}, "Ok!"),
    (r"\b(muda|mudo|silencia|silenciar)\b.*\b(tv|televisão|televisao)\b", "manage_tv", {"action": "mute"}, "Ok!"),
    (r"\b(tira|tirar)\b.*\bmudo\b.*\b(tv|televisão|televisao)\b", "manage_tv", {"action": "unmute"}, "Ok!"),
    (r"\b(aumenta|aumentar|sobe|subir)\b.*\b(volume|som)\b", "manage_tv", {"action": "volume_up"}, "Ok!"),
    (r"\b(abaixa|abaixar|diminui|diminuir)\b.*\b(volume|som)\b", "manage_tv", {"action": "volume_down"}, "Ok!"),
    (r"\b(abre|abrir|coloca|colocar)\b.*\b(?P<app>netflix|youtube|spotify|prime|globoplay|disney|hbo|apple tv)\b", "manage_tv", {"action": "open_app"}, "Ok!"),
    
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
        text = text.strip()
        matched_tv_actions = []
        tv_resp = None
        
        for regex, tool, args, resp in self.compiled_routes:
            match = regex.search(text)
            if match:
                if tool == "manage_tv":
                    final_args = dict(args)
                    if "app" in match.groupdict() and match.group("app"):
                        final_args["app_name"] = match.group("app").lower()
                    matched_tv_actions.append(final_args)
                    tv_resp = resp
                else:
                    logger.info(f"FastSemanticRouter interceptou: '{text}' -> {tool}")
                    return tool, args, resp
        
        if matched_tv_actions:
            logger.info(f"FastSemanticRouter interceptou TV (Lote): '{text}' -> {matched_tv_actions}")
            return "manage_tv", {"actions": matched_tv_actions}, tv_resp
            
        return None
