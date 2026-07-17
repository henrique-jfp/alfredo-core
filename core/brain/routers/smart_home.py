"""
Rotas semânticas para controle de dispositivos inteligentes (luzes, ventiladores,
tomadas). Permite que comandos como "liga a luz da sala" sejam interceptados
em <5ms sem passar pelo Gemini (economizando ~3-5s e dependência de internet).

Usa `custom_parser` em vez de regex puro porque precisamos extrair o cômodo
da frase (named groups são ignorados em rotas não-batchable no semantic_router).

Ordem importa: o semantic router retorna na primeira rota que bater.
"""
import re
from core.brain.semantic_router import Route, normalize

# ── Palavras-chave ──────────────────────────────────────────────────────
# Ações
_ACTIONS_ON = {"liga", "ligar", "acende", "acender", "ativa", "ativar", "ascende", "ascender"}
_ACTIONS_OFF = {"desliga", "desligar", "apaga", "apagar", "desativa", "desativar", "apague"}

# Dispositivos
_WORDS_LIGHT = {"luz", "luzes", "lampada", "lampadas", "luminaria"}
_WORDS_FAN = {"ventilador", "ventiladores", "ventoinha"}
_WORDS_SWITCH = {"tomada", "tomadas"}

# Cômodos (mais específicos primeiro para evitar falsos positivos)
_ROOM_MAP = [
    (["quarto da laura", "quarto laura"], "quarto da laura"),
    (["quarto do casal", "quarto casal"], "quarto do casal"),
    (["sala de jantar", "sala jantar"], "sala de jantar"),
    (["sala de estar"], "sala de estar"),
    (["sala"], "sala"),
    (["quarto"], "quarto"),
    (["escritorio"], "escritorio"),
    (["cozinha"], "cozinha"),
    (["varanda", "sacada"], "varanda"),
    (["banheiro", "wc"], "banheiro"),
    (["lavanderia", "area de servico", "area de serviço"], "lavanderia"),
    (["jardim", "quintal", "area externa", "area externa"], "jardim"),
    (["garagem"], "garagem"),
]


def _has_word(text: str, word_or_phrase: str) -> bool:
    """Casa palavra/frase inteira (com \\b), não substring solta."""
    return re.search(rf"\b{re.escape(word_or_phrase)}\b", text) is not None


def _extract_room(text: str) -> str | None:
    """Extrai o nome do cômodo do texto normalizado."""
    for phrases, room_name in _ROOM_MAP:
        for phrase in phrases:
            if _has_word(text, phrase):
                return room_name
    return None


def _has_any_word(text: str, words: set) -> bool:
    """True se texto contiver qualquer palavra do conjunto (match inteiro)."""
    for w in words:
        if _has_word(text, w):
            return True
    return False


def _parse_smart_home(text: str) -> list[dict] | None:
    """
    Parser customizado para comandos de dispositivos inteligentes.
    Retorna uma lista com 1 dict de argumentos para a tool manage_smart_device,
    ou None se não for um comando de smart home.
    """
    text = normalize(text)

    # 1. Determinar ação
    is_on = _has_any_word(text, _ACTIONS_ON)
    is_off = _has_any_word(text, _ACTIONS_OFF)

    if not is_on and not is_off:
        return None

    # 2. Determinar tipo de dispositivo
    is_light = _has_any_word(text, _WORDS_LIGHT)
    is_fan = _has_any_word(text, _WORDS_FAN)
    is_switch = _has_any_word(text, _WORDS_SWITCH)

    if not is_light and not is_fan and not is_switch:
        return None

    # 3. Montar args
    device_type = None
    if is_light:
        device_type = "light"
    elif is_fan:
        device_type = "fan"
    elif is_switch:
        device_type = "switch"

    action = "turn_on" if is_on else "turn_off"

    args = {"action": action, "device_type": device_type}

    # 4. Extrair cômodo
    room = _extract_room(text)
    if room:
        args["target_room"] = room

    return [args]


# ── Rotas ───────────────────────────────────────────────────────────────
# Usamos uma ÚNICA rota com custom_parser, que cobre todos os casos
# (liga/desliga + luz/ventilador/tomada + cômodo opcional).
ROUTES = [
    Route(
        r".*",  # pattern genérico — o parser decide se é comando válido
        "manage_smart_device",
        {},  # args default (serão sobrescritos pelo parser)
        None,
        False,
        custom_parser=_parse_smart_home,
    ),
]
