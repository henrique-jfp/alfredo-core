import re
import logging
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List, Pattern

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
    pattern: Pattern
    tool: str
    args: Dict[str, Any]
    response: Optional[str] = None
    batchable: bool = False


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


# Mensagens padrão por ação de TV (usadas para montar a resposta do lote)
_TV_MESSAGES = {
    "power_on": "Ligando a TV.",
    "power_off": "Desligando a TV.",
    "mute": "Silenciando a TV.",
    "unmute": "Tirando o mudo da TV.",
    "volume_up": "Aumentando o volume.",
    "volume_down": "Abaixando o volume.",
}


def _tv_response(action: Dict[str, Any]) -> str:
    if action["action"] == "open_app":
        app_name = action.get("app_name", "app").title()
        return f"Abrindo {app_name}."
    return _TV_MESSAGES.get(action["action"], "Ok!")


# Cada item: (pattern_ascii, tool, args, response, batchable)
# IMPORTANTE: patterns já assumem texto normalizado (sem acento, lowercase).
# Usamos _and(...) (lookaheads) em vez de ".*" sequencial para que a ordem
# das palavras na frase não importe: "liga a tv" e "a tv, liga" casam igual.
_TV = "tv|televisao"

_ROUTE_DEFS: List[Tuple[str, str, Dict[str, Any], Optional[str], bool]] = [
    # ---- GERENCIAMENTO DE TV (suporta multi-comandos na mesma frase) ----
    (_and("liga|ligar", _TV),
     "manage_tv", {"action": "power_on"}, None, True),

    (_and("desliga|desligar|apaga|apagar", _TV),
     "manage_tv", {"action": "power_off"}, None, True),

    # unmute PRECISA vir antes de mute: exige "tira/tirar" + "mudo" + tv,
    # ou o verbo "desmuta/desmutar" + tv.
    (rf"(?:{_and(_TV, 'mudo', 'tira|tirar')})|(?:{_and(_TV, 'desmuta|desmutar')})",
     "manage_tv", {"action": "unmute"}, None, True),

    # mute: "silencia/muta a tv" OU "mudo" associado à tv — mas NUNCA se
    # "tira/tirar/desmuta/desmutar" também estiver na frase (aí é unmute).
    (_and(_TV, "silencia|silenciar|muta|mutar|mudo") + _not("tira|tirar|desmuta|desmutar"),
     "manage_tv", {"action": "mute"}, None, True),

    (_and("aumenta|aumentar|sobe|subir", "volume|som"),
     "manage_tv", {"action": "volume_up"}, None, True),

    (_and("abaixa|abaixar|diminui|diminuir", "volume|som"),
     "manage_tv", {"action": "volume_down"}, None, True),

    (r"(?=.*\b(?:abre|abri|abrir|coloca|colocar)\b)"
     r"(?=.*\b(?P<app>netflix|youtube|spotify|prime|globoplay|disney|hbo|apple tv|claro tv|claro)\b)",
     "manage_tv", {"action": "open_app"}, None, True),

    # ---- MÚSICA E MÍDIA ----
    (_and("para|parar|pausa|pausar", "musica|som|spotify"),
     "manage_music", {"action": "pause"}, "Pausando a música.", False),

    # "toca/tocar/continua" = retomar. "volta/voltar" fica só na regra de
    # "previous" abaixo, de propósito, para não colidir com ela.
    (_and("toca|tocar|continua|continuar", "musica|som|spotify"),
     "manage_music", {"action": "resume"}, "Voltando a música.", False),

    (_and("proxima|pula|pular", "musica|som|faixa"),
     "manage_music", {"action": "next"}, "Próxima música.", False),

    (_and("anterior|volta|voltar", "musica|som|faixa"),
     "manage_music", {"action": "previous"}, "Música anterior.", False),

    # ---- TEMPO E DATA ----
    # response=None -> deixa a skill/LLM processar a string exata.
    # Usa (?=.*...) em vez de \b...\b "cru" para continuar funcionando
    # mesmo com prefixo, ex: "alfredo, que horas são".
    (r"(?=.*\bque horas sao\b)", "get_time", {"request_type": "time"}, None, False),
    (r"(?=.*\bque dia e hoje\b)", "get_time", {"request_type": "date"}, None, False),

    # ---- CLIMA ----
    (_and("como esta o|previsao do", "clima|tempo"),
     "get_weather", {"location": "current"}, None, False),
]


class FastSemanticRouter:
    def __init__(self, route_defs: Optional[List[Tuple]] = None):
        route_defs = route_defs if route_defs is not None else _ROUTE_DEFS
        self.routes: List[Route] = [
            Route(pattern=re.compile(pattern), tool=tool, args=args,
                  response=resp, batchable=batchable)
            for pattern, tool, args, resp, batchable in route_defs
        ]

    def match(self, text: str) -> Optional[Tuple[str, Dict[str, Any], Optional[str]]]:
        normalized = normalize(text)

        # agrupa ações batchable por ferramenta (hoje só manage_tv usa isso)
        batched_actions: Dict[str, List[Dict[str, Any]]] = {}

        for route in self.routes:
            # match() em vez de search(): os patterns usam apenas lookaheads
            # (zero-width) que já variam ".*" internamente, então precisam
            # ser avaliados a partir de uma única posição fixa (o início).
            # Com search(), um (?!.*palavra_proibida) podia falhar na
            # posição 0 mas "passar" numa posição mais à frente, já com a
            # palavra proibida para trás do cursor — reintroduzindo bugs
            # de falso-positivo.
            m = route.pattern.match(normalized)
            if not m:
                continue

            if route.batchable:
                args = dict(route.args)
                if "app" in m.groupdict() and m.group("app"):
                    args["app_name"] = m.group("app").lower()
                # evita duplicar a mesma ação se duas regras baterem no mesmo texto
                bucket = batched_actions.setdefault(route.tool, [])
                if args not in bucket:
                    bucket.append(args)
            else:
                logger.info("FastSemanticRouter interceptou: '%s' -> %s", text, route.tool)
                return route.tool, route.args, route.response

        if batched_actions:
            # hoje só há uma ferramenta batchable (manage_tv); se isso mudar
            # no futuro, cada ferramenta batchable vira um match separado.
            tool, actions = next(iter(batched_actions.items()))
            response = " ".join(_tv_response(a) for a in actions) if tool == "manage_tv" else None
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
        "tira o mudo da tv",          # antes colidia com mute
        "coloca a tv no mudo",        # antes falhava (ordem invertida)
        "silencia a televisão",
        "desmuta a tv",
        "abre o netflix",
        "liga a tv e abre o netflix", # multi-comando no mesmo lote
        "toca a música",              # deve ser resume, não previous
        "volta a música",             # deve ser previous
        "música anterior",            # antes falhava (ordem invertida)
        "anterior música",
        "que horas são",
        "alfredo, que horas são",      # com prefixo antes da frase-chave
        "como está o clima",
        "isso não deveria bater em nada",
    ]

    for case in test_cases:
        result = router.match(case)
        print(f"{case!r:45} -> {result}")
