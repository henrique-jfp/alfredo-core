"""
Rotas semânticas para controle de dispositivos inteligentes (luzes, ventiladores,
tomadas). Permite que comandos como "liga a luz da sala" sejam interceptados
em <5ms sem passar pelo Gemini (economizando ~3-5s e dependência de internet).

Usa `custom_parser` em vez de regex puro porque precisamos extrair o cômodo
da frase (named groups são ignorados em rotas não-batchable no semantic_router).

Ordem importa: o semantic router retorna na primeira rota que bater.

v2 – Data-driven: lê os cômodos de house_context.yaml (seção 'ambientes'),
     suporta velocidade de ventilador (1-6), ventilação/exaustão, desligar
     tudo, múltiplos sinônimos de ação, e múltiplos dispositivos na mesma
     frase ("liga a luz e o ventilador da sala").
"""
import re
import logging
import pathlib
import yaml
from core.brain.semantic_router import Route, normalize

logger = logging.getLogger("alfredo.smart_home_router")

# ═══════════════════════════════════════════════════════════════════════════
# CARREGAMENTO DE CÔMODOS A PARTIR DO YAML (data-driven)
# ═══════════════════════════════════════════════════════════════════════════

_YAML_PATH = pathlib.Path(__file__).resolve().parents[3] / "house" / "house_context.yaml"


def _load_ambientes() -> list[tuple[list[str], str, str]]:
    """Retorna [(nomes_falados, room_id, scene_prefix), …] ordenados
    do mais específico (mais palavras no nome) para o mais genérico,
    garantindo que "quarto da laura" case antes de "quarto" sozinho."""
    try:
        with open(_YAML_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ambientes = data.get("ambientes", [])
    except Exception as e:
        logger.error(f"Falha ao carregar ambientes de {_YAML_PATH}: {e}")
        ambientes = []

    result = []
    for amb in ambientes:
        room_id = amb["id"]
        names = [normalize(n) for n in amb.get("names", [])]
        prefix = amb.get("scene_prefix", "")
        result.append((names, room_id, prefix))

    # Ordena: nomes mais longos primeiro (evita "sala" casar antes de "sala de jantar")
    result.sort(key=lambda x: -max((len(n) for n in x[0]), default=0))
    return result


# Carrega uma vez na importação (o YAML quase nunca muda em runtime)
_ROOM_MAP = _load_ambientes()


# ═══════════════════════════════════════════════════════════════════════════
# PALAVRAS-CHAVE (frozensets para lookup O(1))
# ═══════════════════════════════════════════════════════════════════════════

# Ações
_ACTIONS_ON = frozenset({
    "liga", "ligar", "acende", "acender", "ativa", "ativar",
    "ascende", "ascender", "abrir", "abre", "coloca", "colocar",
    "coloque", "bota", "botar", "poe", "por",
})
_ACTIONS_OFF = frozenset({
    "desliga", "desligar", "apaga", "apagar", "desativa", "desativar",
    "apague", "fecha", "fechar", "tira", "tirar", "remove", "remover",
    "para", "parar",
})
_ACTIONS_TOGGLE = frozenset({"alterna", "alternar"})

# Dispositivos
_WORDS_LIGHT = frozenset({
    "luz", "luzes", "lampada", "lampadas", "luminaria", "luminarias",
    "iluminacao", "abajur",
})
_WORDS_FAN = frozenset({
    "ventilador", "ventiladores", "ventoinha", "ventoinhas",
})
_WORDS_VENTILATION = frozenset({"ventilacao", "ventilar"})
_WORDS_EXHAUST = frozenset({"exaustao", "exaustor", "exaustores"})
_WORDS_SWITCH = frozenset({"tomada", "tomadas", "interruptor"})
_WORDS_ALL = frozenset({"tudo", "todas", "todos"})
_WORDS_TV = frozenset({"tv", "televisao", "televisão"})

# Mapa de velocidades faladas → número (1-6)
_SPEED_WORDS = {
    "1": "1", "um": "1", "uma": "1", "baixa": "1", "minima": "1", "minimo": "1",
    "2": "2", "dois": "2", "duas": "2",
    "3": "3", "tres": "3", "media": "3", "medio": "3",
    "4": "4", "quatro": "4",
    "5": "5", "cinco": "5", "alta": "5", "alto": "5",
    "6": "6", "seis": "6", "maxima": "6", "maximo": "6", "turbo": "6",
}

# Mapa de cores faladas → RGB (para lâmpada do escritório)
_COLOR_MAP = {
    "azul": [0, 0, 255],
    "vermelho": [255, 0, 0],
    "vermelha": [255, 0, 0],
    "verde": [0, 255, 0],
    "amarelo": [255, 255, 0],
    "amarela": [255, 255, 0],
    "roxo": [128, 0, 128],
    "roxa": [128, 0, 128],
    "rosa": [255, 105, 180],
    "laranja": [255, 165, 0],
    "branco": [255, 255, 255],
    "branca": [255, 255, 255],
    "quente": [255, 180, 100],
    "frio": [200, 220, 255],
    "fria": [200, 220, 255],
    "ciano": [0, 255, 255],
}
_WORDS_COLOR = frozenset({"cor", "cores", "colorir", "colorida", "colorido"})


# ═══════════════════════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════

def _has_word(text: str, word_or_phrase: str) -> bool:
    """Casa palavra/frase inteira (com \\b), não substring solta."""
    return re.search(rf"\b{re.escape(word_or_phrase)}\b", text) is not None


def _has_any(text: str, words: frozenset) -> bool:
    """True se texto contiver qualquer palavra do conjunto (match inteiro)."""
    for w in words:
        if _has_word(text, w):
            return True
    return False


def _extract_room(text: str) -> tuple[str, str] | None:
    """Extrai o cômodo do texto normalizado.
    Retorna (room_id, scene_prefix) ou None."""
    for names, room_id, prefix in _ROOM_MAP:
        for name in names:
            if _has_word(text, name):
                return room_id, prefix
    return None


def _extract_speed(text: str) -> str | None:
    """Extrai velocidade do ventilador do texto.
    Retorna string "1"-"6" ou None.
    Aceita padrões como:
      - "ventilador no 3"
      - "ventilador velocidade alta"
      - "ventilador 3"
    """
    # Padrão 1: "no/na/velocidade/nivel N"
    m = re.search(r'(?:no|na|velocidade|nivel|nível)\s*(\w+)', text)
    if m:
        val = _SPEED_WORDS.get(m.group(1))
        if val:
            return val

    # Padrão 2: "ventilador N" (número direto depois de ventilador)
    m = re.search(r'ventilador(?:es)?\s+(\d)', text)
    if m:
        n = m.group(1)
        if n in "123456":
            return n

    # Padrão 3: palavras soltas de velocidade
    tokens = text.split()
    for tok in tokens:
        if tok in _SPEED_WORDS and tok not in {"um", "uma"}:  # "um" é muito ambíguo
            return _SPEED_WORDS[tok]

    return None


def _extract_color(text: str) -> list[int] | None:
    """Extrai cor RGB do texto.
    Aceita padrões como:
      - 'luz azul'
      - 'cor vermelha'
      - 'deixa a luz verde'
    Retorna [R, G, B] ou None.
    """
    for color_name, rgb in _COLOR_MAP.items():
        if _has_word(text, color_name):
            return rgb
    return None


# ═══════════════════════════════════════════════════════════════════════════
# PARSER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

def _parse_smart_home(text: str) -> list[dict] | None:
    """
    Parser customizado para comandos de dispositivos inteligentes.
    Retorna uma lista de dicts de argumentos para a tool manage_smart_device,
    ou None se não for um comando de smart home.

    Suporta:
      - Luz: "liga a luz", "apaga a luz do quarto da laura"
      - Ventilador velocidade: "coloca ventilador no 3", "ventilador 3 da sala"
      - Ventilador genérico: "liga o ventilador", "desliga o ventilador"
      - Ventilação/Exaustão: "liga a ventilacao", "exaustao do quarto"
      - Desligar tudo: "desliga tudo da sala", "apaga tudo"
      - Múltiplos dispositivos: "liga a luz e o ventilador da sala"
    """
    text = normalize(text)

    # Remove prefixos de wake-word ("alexa", "alex", "alfred", etc.)
    text = re.sub(r"^(alexa?|alfredo?|ok google|hey google|ei google)\b[,.]?\s*", "", text)

    # Detecta cômodo
    room_info = _extract_room(text)
    room_id = room_info[0] if room_info else None
    scene_prefix = room_info[1] if room_info else None

    # Detecta ação (último verbo ganha se houver conflito)
    is_on = _has_any(text, _ACTIONS_ON)
    is_off = _has_any(text, _ACTIONS_OFF)
    is_toggle = _has_any(text, _ACTIONS_TOGGLE)

    # Se tem "desliga" e "liga" ao mesmo tempo, último verbo na frase ganha
    if is_on and is_off:
        last_on = max((text.rfind(w) for w in _ACTIONS_ON if _has_word(text, w)), default=-1)
        last_off = max((text.rfind(w) for w in _ACTIONS_OFF if _has_word(text, w)), default=-1)
        if last_off > last_on:
            is_on = False
        else:
            is_off = False

    if not is_on and not is_off and not is_toggle:
        # Exceções: "ventilador 3" ou "luz vermelha" → sem verbo, assumir "ligar"
        has_fan_implicit = _has_any(text, _WORDS_FAN)
        speed_implicit = _extract_speed(text) if has_fan_implicit else None
        has_color_implicit = _extract_color(text) is not None

        if speed_implicit or has_color_implicit:
            is_on = True  # Tratar como "ligar"
        else:
            return None  # Sem ação detectada → não é comando smart home

    # Detecta dispositivos mencionados
    has_light = _has_any(text, _WORDS_LIGHT)
    has_fan = _has_any(text, _WORDS_FAN)
    has_ventilation = _has_any(text, _WORDS_VENTILATION)
    has_exhaust = _has_any(text, _WORDS_EXHAUST)
    has_switch = _has_any(text, _WORDS_SWITCH)
    has_all = _has_any(text, _WORDS_ALL)
    has_tv = _has_any(text, _WORDS_TV)

    # Se nenhum dispositivo específico foi mencionado, verifica se é "desliga tudo"
    has_any_device = has_light or has_fan or has_ventilation or has_exhaust or has_switch or has_tv

    if not has_any_device and not has_all:
        return None  # Nenhum dispositivo mencionado → não é smart home

    # Determina ação base
    if is_toggle:
        base_action = "toggle"
    elif is_off:
        base_action = "turn_off"
    else:
        base_action = "turn_on"

    # ── Monta a lista de comandos ────────────────────────────────────
    commands = []

    def _add_cmd(**kwargs):
        cmd = {"action": base_action}
        if room_id:
            cmd["target_room"] = room_id
        if scene_prefix:
            cmd["scene_prefix"] = scene_prefix
        cmd.update(kwargs)
        commands.append(cmd)

    # 1. "Desliga tudo" / "Desliga a sala" → manda acionar cena master de desligar
    if has_all and is_off:
        _add_cmd(device_name="desligar", action="turn_off")
        return commands

    # 1b. "Desliga a sala" (sem dispositivo específico, só cômodo) → master off
    if not has_any_device and not has_all and is_off and room_id:
        _add_cmd(device_name="desligar", action="turn_off")
        return commands

    # 2. Ventilação
    if has_ventilation:
        _add_cmd(device_type="ventilation")
        # Se TAMBÉM tem outros dispositivos, continua montando
        if not has_light and not has_fan and not has_exhaust:
            return commands

    # 3. Exaustão
    if has_exhaust:
        _add_cmd(device_type="exhaust")
        if not has_light and not has_fan:
            return commands

    # 4. Ventilador
    if has_fan:
        speed = _extract_speed(text)
        if speed:
            _add_cmd(device_type="fan", device_name=f"ventilador {speed}", action="turn_on")
        elif is_off:
            _add_cmd(device_type="fan", action="turn_off")
        else:
            # Ligar ventilador sem velocidade → default velocidade 3
            _add_cmd(device_type="fan", device_name="ventilador 3", action="turn_on")

    # 5. Luz
    if has_light:
        # Verifica se pediu uma cor (ex: "luz azul", "deixa a luz vermelha")
        color_rgb = _extract_color(text)
        if color_rgb:
            # Cor sempre vai pro escritório (única lâmpada RGB da casa)
            _add_cmd(device_type="light", action="set_color",
                     target_room="ROOM_OFFICE", scene_prefix="escritorio",
                     color=color_rgb)
        else:
            # Toggle normal (mesma cena liga/desliga)
            _add_cmd(device_type="light")

    # 5b. Cor sem mencionar "luz" (ex: "alexa cor azul", "coloca azul no escritório")
    if not has_light and _has_any(text, _WORDS_COLOR):
        color_rgb = _extract_color(text)
        if color_rgb:
            _add_cmd(device_type="light", action="set_color",
                     target_room="ROOM_OFFICE", scene_prefix="escritorio",
                     color=color_rgb)

    # 5c. Cor sem nenhum keyword de luz/cor (ex: "alexa azul no escritório")
    if not has_light and not _has_any(text, _WORDS_COLOR) and not commands:
        color_rgb = _extract_color(text)
        if color_rgb and room_id == "ROOM_OFFICE":
            _add_cmd(device_type="light", action="set_color", color=color_rgb)

    # 6. Tomada
    if has_switch:
        _add_cmd(device_type="switch")
        
    # 7. TV (IR)
    if has_tv:
        if scene_prefix in ["casal", "quarto_laura", "escritorio"]:
            _add_cmd(device_type="tv")
        elif not commands:
            return None  # Deixa para o TVSkill (Samsung TV) APENAS se for o único comando

    if commands:
        return commands

    return None


# ═══════════════════════════════════════════════════════════════════════════
# ROTAS
# ═══════════════════════════════════════════════════════════════════════════
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
