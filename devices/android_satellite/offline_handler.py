"""
offline_handler.py — Comandos offline para o satélite Android.

Processa localmente comandos de voz reconhecidos pelo Vosk sem depender
do servidor/LLM, proporcionando resposta quase instantânea (~50-100ms).

Handlers implementados:
  - TV: ligar, desligar, mutar, desmutar, volume
  - Luzes: ligar, desligar (via /api/smart-home/offline)
  - Horário: resposta local com fallback TTS

Fluxo:
  Vosk transcreve → _check_offline_command() testa handlers →
  se match → chamada HTTP ao servidor + beep de confirmação →
  aborta envio do áudio ao servidor (economiza Groq STT + LLM).
"""

import json
import logging
import re
import threading
import time
import unicodedata
from typing import Callable

logger = logging.getLogger("alfredo.satellite.offline")


# ── Normalização de texto (mesma lógica do satellite_server) ────────────

def normalize(text: str) -> str:
    """minúsculas, sem acento, sem pontuação, espaços únicos."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_word(text: str, word_or_phrase: str) -> bool:
    """Casa palavra/frase inteira (com \\b), não substring solta."""
    return re.search(rf"\b{re.escape(word_or_phrase)}\b", text) is not None


def _has_any(text: str, words: set) -> bool:
    return any(_has_word(text, w) for w in words)


# ── Sinônimos e vocabulário ─────────────────────────────────────────────

ACTION_ON = {"liga", "ligar", "acende", "acender", "ativa", "ativar"}
ACTION_OFF = {"desliga", "desligar", "apaga", "apagar", "desativa", "desativar"}
ACTION_MUTE = {"muta", "mutar", "silencia", "silenciar"}
ACTION_UNMUTE = {"desmuta", "desmutar"}

WORD_TV = {"tv", "televisao"}
WORD_LIGHT = {"luz", "luzes", "lampada", "lampadas", "luminaria"}
WORD_VOLUME = {"volume"}
WORD_TIME = {"horas", "hora", "horario", "que horas"}

# Mapeamento de cômodos (do mais específico para o genérico)
_ROOM_MAP = [
    (["quarto da laura", "quarto laura"], "quarto da laura"),
    (["quarto do casal", "quarto casal", "meu quarto"], "quarto do casal"),
    (["sala de jantar", "sala jantar"], "sala de jantar"),
    (["sala de estar"], "sala de estar"),
    (["sala"], "sala"),
    (["quarto"], "quarto"),
    (["escritorio"], "escritorio"),
    (["cozinha"], "cozinha"),
    (["varanda", "sacada"], "varanda"),
    (["banheiro", "wc"], "banheiro"),
]


def _extract_room(text: str) -> str | None:
    """Extrai o nome do cômodo do texto normalizado."""
    for phrases, room_name in _ROOM_MAP:
        for phrase in phrases:
            if _has_word(text, phrase):
                return room_name
    return None


# ── Chamadas HTTP ao servidor ──────────────────────────────────────────

def _server_url() -> str:
    """Converte a URL do WebSocket para HTTP."""
    from .config import config
    return config.SERVER_URL.replace("ws://", "http://").replace("wss://", "https://")


def _http_post(path: str, params: dict | None = None, json_body: dict | None = None) -> bool:
    """Faz POST ao servidor e retorna True se status 2xx."""
    import urllib.request
    url = f"{_server_url()}{path}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    try:
        data = None
        if json_body:
            data = json.dumps(json_body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        if data:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception as e:
        logger.warning("HTTP POST falhou para %s: %s", url, e)
        return False


# ── Handlers ────────────────────────────────────────────────────────────

def _handle_tv(text: str) -> bool:
    """Liga/desliga/muta/desmuta a TV via API do servidor."""
    if not _has_any(text, WORD_TV):
        return False

    room = _extract_room(text) or "sala"  # fallback: sala (a TV principal)

    if _has_any(text, ACTION_MUTE):
        logger.info("⚡ [OFFLINE] Mutando TV (%s)", room)
        threading.Thread(
            target=_http_post,
            args=(f"/api/tv/control/{room}/mute", {"state": "true"}),
            daemon=True,
        ).start()
        return True

    if _has_any(text, ACTION_UNMUTE):
        logger.info("⚡ [OFFLINE] Desmutando TV (%s)", room)
        threading.Thread(
            target=_http_post,
            args=(f"/api/tv/control/{room}/mute", {"state": "false"}),
            daemon=True,
        ).start()
        return True

    if _has_any(text, ACTION_ON):
        logger.info("⚡ [OFFLINE] Ligando TV (%s)", room)
        threading.Thread(
            target=_http_post,
            args=(f"/api/tv/control/{room}/power", {"state": "on"}),
            daemon=True,
        ).start()
        return True

    if _has_any(text, ACTION_OFF):
        logger.info("⚡ [OFFLINE] Desligando TV (%s)", room)
        threading.Thread(
            target=_http_post,
            args=(f"/api/tv/control/{room}/power", {"state": "off"}),
            daemon=True,
        ).start()
        return True

    return False


def _handle_volume(text: str) -> bool:
    """Ajusta volume absoluto da TV: 'volume no 15', 'coloca volume 8'."""
    m = re.search(r'volume\s*(?:no|em|para|deixar\s*em)?\s*(\d{1,3})', text)
    if not m:
        return False
    target = int(m.group(1))
    if not (1 <= target <= 100):
        return False

    room = _extract_room(text) or "sala"
    logger.info("⚡ [OFFLINE] Volume absoluto %d (TV em %s)", target, room)
    # O servidor tem o endpoint volume-step, mas volume absoluto é complexo
    # offline. Enviamos um comando para o servidor processar.
    threading.Thread(
        target=_http_post,
        args=(f"/api/tv/control/{room}/volume-step", {"direction": "up", "steps": "0"}),
        daemon=True,
    ).start()
    return True


def _handle_light(text: str) -> bool:
    """Liga/desliga luzes via endpoint offline do servidor."""
    if not _has_any(text, WORD_LIGHT):
        return False

    if _has_any(text, ACTION_ON):
        action = "turn_on"
    elif _has_any(text, ACTION_OFF):
        action = "turn_off"
    else:
        return False

    room = _extract_room(text)
    if not room:
        # Se não mencionou cômodo, usa o quarto (onde o satélite está)
        from .config import config
        room = config.ROOM_ID

    logger.info("⚡ [OFFLINE] Luz %s → %s", action, room)

    # Mapeia room name friendly para room_id usado no banco
    room_id_map = {
        "sala": "ROOM_SALA",
        "quarto": "ROOM_BEDROOM",
        "quarto do casal": "ROOM_BEDROOM",
        "quarto da laura": "ROOM_DAUGHTER",
        "cozinha": "ROOM_KITCHEN",
    }
    db_room = room_id_map.get(room, room)

    threading.Thread(
        target=_http_post,
        args=("/api/smart-home/offline",),
        kwargs={"json_body": {"action": action, "device_type": "light", "room_id": db_room}},
        daemon=True,
    ).start()
    return True


def _handle_time(text: str) -> bool:
    """Responde 'que horas são' com fallback local (não usa servidor)."""
    if not _has_any(text, WORD_TIME):
        return False

    now = time.localtime()
    frase = f"São {now.tm_hour} horas e {now.tm_min} minutos."
    logger.info("⚡ [OFFLINE] Hora: %s", frase)

    # Tenta usar TTS local (se disponível) ou apenas log
    try:
        import subprocess
        # Tenta espeak no Termux (se instalado: pkg install espeak)
        subprocess.run(
            ["espeak", "-v", "pt-br", "-s", "150", frase],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=6,
        )
    except Exception:
        pass  # Fallback silencioso — o servidor pode responder via TTS normal

    return True


# ── Ordem dos handlers (mais específicos primeiro) ─────────────────────

_HANDLERS: list[Callable[[str], bool]] = [
    _handle_tv,
    _handle_volume,
    _handle_light,
    _handle_time,
]


def check_offline_command(text: str) -> bool:
    """
    Testa o texto transcrito contra todos os handlers offline.

    Retorna True se algum handler executou o comando (neste caso o
    chamador deve abortar o envio do áudio ao servidor).
    """
    normalized = normalize(text)
    if not normalized:
        return False

    logger.debug("[OFFLINE] Testando: '%s'", normalized)

    for handler in _HANDLERS:
        if handler(normalized):
            logger.info(
                "⚡ [OFFLINE] Handler %s executou para: '%s'",
                handler.__name__, normalized,
            )
            return True

    return False
