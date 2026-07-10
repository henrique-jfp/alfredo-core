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
    act = action["action"]

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


# Cada item: (pattern_ascii, tool, args, response, batchable)
# IMPORTANTE: patterns já assumem texto normalizado (sem acento, lowercase).
# Usamos _and(...) (lookaheads) em vez de ".*" sequencial para que a ordem
# das palavras na frase não importe: "liga a tv" e "a tv, liga" casam igual.
_TV = "tv|televisao"

# Lista de canais abertos conhecidos (fácil de estender). Usada tanto para
# "muda pro globo" (canal nativo da tv) quanto para "muda o canal do claro
# tv+ pro globo" (canal dentro do app).
_CHANNEL_NAMES = "globo|sbt|record|band|redetv|cultura|sportv|globonews|gnt|multishow|premiere|combate"

# Apps reconhecidos (Home Assistant costuma expor isso via media_player
# select_source ou play_media, dependendo da integração da sua TV).
_APPS = "netflix|youtube|spotify|prime|globoplay|disney|hbo|apple tv|claro tv\\+|claro tv|claro"

_ROUTE_DEFS: List[Tuple[str, str, Dict[str, Any], Optional[str], bool]] = [
    # ---- ENERGIA ----
    (_and("liga|ligar", _TV),
     "manage_tv", {"action": "power_on"}, None, True),

    (_and("desliga|desligar|apaga|apagar", _TV),
     "manage_tv", {"action": "power_off"}, None, True),

    # ---- MUDO ----
    # unmute PRECISA vir antes de mute: exige "tira/tirar" + "mudo" + tv,
    # ou o verbo "desmuta/desmutar" + tv.
    (rf"(?:{_and(_TV, 'mudo', 'tira|tirar')})|(?:{_and(_TV, 'desmuta|desmutar')})",
     "manage_tv", {"action": "unmute"}, None, True),

    # mute: "silencia/muta a tv" OU "mudo" associado à tv — mas NUNCA se
    # "tira/tirar/desmuta/desmutar" também estiver na frase (aí é unmute).
    (_and(_TV, "silencia|silenciar|muta|mutar|mudo") + _not("tira|tirar|desmuta|desmutar"),
     "manage_tv", {"action": "mute"}, None, True),

    # ---- VOLUME ----
    # volume com número específico ("coloca o volume em 20") vem antes das
    # regras genéricas de aumentar/abaixar, para não bater nas duas ao
    # mesmo tempo (aqui não há conflito de regex, mas mantém a leitura
    # lógica: primeiro o caso mais específico).
    (_and("coloca|colocar|ajusta|ajustar|deixa|deixar|poe|por|muda|mudar", "volume")
     + r"(?=.*\b(?P<level>\d{1,3})\b)",
     "manage_tv", {"action": "volume_set"}, None, True),

    (_and("aumenta|aumentar|sobe|subir", "volume|som"),
     "manage_tv", {"action": "volume_up"}, None, True),

    (_and("abaixa|abaixar|diminui|diminuir", "volume|som"),
     "manage_tv", {"action": "volume_down"}, None, True),

    # ---- ENTRADA / FONTE (HDMI, AV, antena) ----
    (r"(?=.*\b(?:muda|mudar|troca|trocar|coloca|colocar|vai|ir)\b)"
     r"(?=.*\b(?P<source>hdmi\s?[123])\b)",
     "manage_tv", {"action": "select_source"}, None, True),

    (_and("entrada|fonte", r"(?P<source>av|antena|tv aberta)"),
     "manage_tv", {"action": "select_source"}, None, True),

    # ---- CANAL (sintonizador nativo da tv — NÃO dentro de um app) ----
    # excluem "claro" de propósito: canal dentro do Claro tv+ é tratado
    # como app_channel_change mais abaixo, pois não é o sintonizador da tv.
    (_and("muda|mudar|troca|trocar|coloca|colocar|vai|ir", "canal")
     + r"(?=.*\b(?P<channel>\d{1,4})\b)" + _not("claro"),
     "manage_tv", {"action": "channel_number"}, None, True),

    (_and("muda|mudar|troca|trocar|coloca|colocar|vai|ir", "canal")
     + rf"(?=.*\b(?P<channel_name>{_CHANNEL_NAMES})\b)" + _not("claro"),
     "manage_tv", {"action": "channel_name"}, None, True),

    # ---- CANAL DENTRO DE UM APP (ex.: Claro tv+) ----
    (r"(?=.*\bclaro\b)" + _and("canal") + r"(?=.*\b(?P<channel>\d{1,4})\b)",
     "manage_tv", {"action": "app_channel_change", "app_name": "claro tv+"}, None, True),

    (r"(?=.*\bclaro\b)" + _and("canal") + rf"(?=.*\b(?P<channel_name>{_CHANNEL_NAMES})\b)",
     "manage_tv", {"action": "app_channel_change", "app_name": "claro tv+"}, None, True),

    # ---- ABRIR APP ----
    (r"(?=.*\b(?:abre|abri|abrir|coloca|colocar)\b)"
     rf"(?=.*\b(?P<app_name>{_APPS})\b)" + _not("canal"),
     "manage_tv", {"action": "open_app"}, None, True),

    # ---- REPRODUÇÃO DE CONTEÚDO (vídeo/série/filme/app de streaming) ----
    # Exige uma palavra de conteúdo OU o nome de um app pra não colidir
    # com manage_music (que exige musica|som|spotify). Se um app for
    # citado, ele é capturado como app_name.
    (r"(?=.*\b(?:play|toca|tocar|reproduz|reproduzir)\b)"
     rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
     "manage_tv", {"action": "media_play"}, None, True),

    # "para/parar" foi excluído de propósito: em português "para" também é
    # preposição ("canal para 63"), então usá-lo como gatilho de pausa
    # gerava falso positivo em qualquer frase com "para" + nome de app.
    (r"(?=.*\b(?:pausa|pausar)\b)"
     rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
     "manage_tv", {"action": "media_pause"}, None, True),

    (r"(?=.*\b(?:encerra|encerrar|sai|sair)\b)"
     rf"(?=.*\b(?:video|filme|serie|programa|episodio|conteudo|(?P<app_name>{_APPS}))\b)",
     "manage_tv", {"action": "media_stop"}, None, True),

    (_and("proximo|proxima|avanca|avancar|pula|pular", "video|filme|serie|programa|episodio"),
     "manage_tv", {"action": "media_next"}, None, True),

    (_and("anterior|volta|voltar", "video|filme|serie|programa|episodio"),
     "manage_tv", {"action": "media_previous"}, None, True),

    # ---- MÚSICA E MÍDIA (Spotify, especificamente) ----
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
                # extrai qualquer grupo nomeado capturado (app_name, level,
                # source, channel, channel_name...) direto pros args —
                # evita ter que listar cada grupo manualmente aqui.
                for key, value in m.groupdict().items():
                    if value:
                        args[key] = value.strip().lower()
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
        "isso não deveria bater em nada",
    ]

    for case in test_cases:
        result = router.match(case)
        print(f"{case!r:45} -> {result}")