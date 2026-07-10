"""
semantic_router.py

Roteador semântico ultra-rápido (Regex / Keywords).
Permite interceptar comandos locais em < 5ms sem depender de chamadas à API LLM.

Ordem de prioridade importa: as primeiras regras não-batchable que baterem
vencem. Regras marcadas como `batchable=True` (hoje, manage_tv) são
acumuladas e retornadas juntas, permitindo multi-comandos na mesma frase
("liga a tv e abre o netflix").
"""

import re
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List, Pattern, Callable

logger = logging.getLogger("alfredo.semantic_router")


# --------------------------------------------------------------------------- #
# Normalização de texto
# --------------------------------------------------------------------------- #
def normalize(text: str) -> str:
    """
    Lowercase + remoção de acentos (NFKD).

    Isso evita ter que escrever "musica|música", "televisao|televisão" etc.
    em toda regra — as regras abaixo já são escritas só em ASCII.
    """
    text = text.strip().lower()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


# --------------------------------------------------------------------------- #
# Definição de rotas
# --------------------------------------------------------------------------- #
@dataclass
class Route:
    pattern: Any  # Pode ser string ou Pattern
    tool: str
    args: Dict[str, Any]
    response: Optional[str] = None
    batchable: bool = False
    custom_parser: Optional[Callable[[str], Optional[List[Dict[str, Any]]]]] = None

    def __post_init__(self):
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern)


def _and(*groups: str) -> str:
    """
    Constrói lookaheads que exigem a presença de cada grupo de palavras,
    em qualquer ordem no texto. Ex: _and("liga|ligar", "tv") casa tanto
    "liga a tv" quanto (hipoteticamente) "a tv, liga".
    """
    return "".join(rf"(?=.*\b(?:{g})\b)" for g in groups)


def _not(*groups: str) -> str:
    """Nega a presença de qualquer palavra dos grupos dados."""
    return "".join(rf"(?!.*\b(?:{g})\b)" for g in groups)


# Mensagens padrão por ação de TV (usadas para montar a resposta do lote).
# Ações com parâmetro dinâmico (canal, volume, fonte...) são tratadas em
# _tv_response(), que consulta esse dict como fallback.
_TV_MESSAGES = {
    "power_on": "Ligando a TV.",
    "power_off": "Desligando a TV.",
    "mute": "Silenciando a TV.",
    "unmute": "Tirando o mudo da TV.",
    "volume_up": "Aumentando o volume.",
    "volume_down": "Abaixando o volume.",
    "media_play": "Retomando a reprodução.",
    "media_pause": "Pausando a reprodução.",
    "media_stop": "Encerrando a reprodução.",
    "media_next": "Avançando para o próximo.",
    "media_previous": "Voltando para o anterior.",
}


def _tv_response(action: Dict[str, Any]) -> str:
    act = action.get("action", "")

    if act == "open_app":
        return f"Abrindo {action.get('app_name', 'app').title()}."

    if act == "volume_set":
        return f"Ajustando o volume para {action.get('level')}."

    if act == "select_source":
        source = action.get("source", "").replace(" ", "").upper()
        return f"Mudando para a entrada {source}."

    if act == "channel_number":
        return f"Mudando para o canal {action.get('channel')}."

    if act == "channel_name":
        return f"Mudando para o canal {action.get('channel_name', '').title()}."

    if act == "app_channel_change":
        app = action.get("app_name", "app").title()
        canal = action.get("channel") or action.get("channel_name", "")
        return f"Mudando o canal do {app} para {str(canal).title()}."

    return _TV_MESSAGES.get(act, "Ok!")


# --------------------------------------------------------------------------- #
# Carregamento Dinâmico de Rotas (Módulo Routers)
# --------------------------------------------------------------------------- #
class FastSemanticRouter:
    def __init__(self, route_defs: Optional[List[Route]] = None):
        if route_defs is not None:
            self.routes = route_defs
        else:
            from core.brain.routers import ROUTES
            self.routes = ROUTES

    def match(self, text: str) -> Optional[Tuple[str, Dict[str, Any], Optional[str]]]:
        normalized = normalize(text)

        # agrupa ações batchable por ferramenta (hoje só manage_tv e manage_timer usam isso)
        batched_actions: Dict[str, List[Dict[str, Any]]] = {}

        for route in self.routes:
            if route.custom_parser:
                # Se tiver parser customizado, delega a ele a busca de múltiplas ações
                parsed_actions = route.custom_parser(normalized)
                if parsed_actions:
                    if route.batchable:
                        bucket = batched_actions.setdefault(route.tool, [])
                        for action in parsed_actions:
                            if action not in bucket:
                                bucket.append(action)
                    else:
                        logger.info("FastSemanticRouter interceptou via parser: '%s' -> %s", text, route.tool)
                        return route.tool, parsed_actions[0] if len(parsed_actions)==1 else {"actions": parsed_actions}, route.response
                continue

            m = route.pattern.match(normalized)
            if not m:
                continue

            if route.batchable:
                args = dict(route.args)
                for key, value in m.groupdict().items():
                    if value:
                        args[key] = value.strip().lower()
                bucket = batched_actions.setdefault(route.tool, [])
                if args not in bucket:
                    bucket.append(args)
            else:
                logger.info("FastSemanticRouter interceptou: '%s' -> %s", text, route.tool)
                return route.tool, route.args, route.response

        if batched_actions:
            # Pega o primeiro bucket que tiver ações (já que iteramos por rotas e agrupamos)
            tool, actions = next(iter(batched_actions.items()))
            if tool == "manage_tv":
                response = " ".join(_tv_response(a) for a in actions)
            elif tool == "manage_timer":
                response = f"Criando {len(actions)} timer{'s' if len(actions)>1 else ''}."
            else:
                response = None
            logger.info("FastSemanticRouter interceptou %s (lote): '%s' -> %s", tool, text, actions)
            return tool, {"actions": actions}, response

        return None


# --------------------------------------------------------------------------- #
# Auto-teste rápido (python semantic_router.py)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    router = FastSemanticRouter()

    test_cases = [
        "liga a tv",
        "tira o mudo da tv",              # antes colidia com mute
        "coloca a tv no mudo",            # antes falhava (ordem invertida)
        "silencia a televisão",
        "desmuta a tv",
        "abre o netflix",
        "liga a tv e abre o netflix",     # multi-comando no mesmo lote
        "coloca o volume em 20",          # volume_set
        "muda para hdmi 2",               # select_source
        "troca a entrada para antena",    # select_source (av/antena)
        "muda para o canal 5",            # channel_number
        "coloca o canal do globo",        # channel_name
        "muda o canal do claro tv+ para 63",     # app_channel_change (número)
        "troca o canal do claro tv pro sbt",     # app_channel_change (nome)
        "pausa o filme",                  # media_pause (conteúdo)
        "toca o claro tv+",               # media_play (com app_name capturado)
        "próximo episódio",               # media_next
        "toca a música",                  # deve ser resume (manage_music), não previous
        "volta a música",                 # deve ser previous (manage_music)
        "música anterior",                # antes falhava (ordem invertida)
        "anterior música",
        "que horas são",
        "alfredo, que horas são",         # com prefixo antes da frase-chave
        "como está o clima",
        "me avisa daqui a 5 minutos e daqui a 10 minutos para tirar o bolo", # timers
        "adiciona pão na lista",
        "o que tem na lista",
        "limpar lista",
        "isso não deveria bater em nada",
    ]

    for case in test_cases:
        result = router.match(case)
        print(f"{case!r:45} -> {result}")