"""
Alfredo Satellite (OpenWakeWord) — captura de áudio, wake word, VAD e streaming
para o servidor via WebSocket.

Refatorado a partir da versão original: mesma lógica e mesmos thresholds
calibrados (nenhum número de tuning foi alterado), mas com:
  - logging estruturado (nível + timestamp) em vez de print() solto
  - estado global agrupado em classes (SatelliteState, AudioConfig)
  - type hints e docstrings
  - tratamento de exceção mais explícito nos pontos críticos (crash-loop debugging)
"""

from __future__ import annotations

import os
import sys

# Precisa vir ANTES de qualquer outro import: garante que stdout/stderr não
# fiquem bufferizados quando rodando sob systemd (sem tty), senão logs somem
# em caso de crash antes do flush.
os.environ["PYTHONUNBUFFERED"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)

import array
import json
import logging
import math
import queue
import re
import signal
import socket
import subprocess
import threading
import time
import unicodedata
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import requests
import sounddevice as sd
import webrtcvad
from websockets.sync.client import connect

# Constantes de resiliência de rede
WS_CONNECT_TIMEOUT = 10        # timeout máximo para estabelecer conexão TCP
WS_RECV_TIMEOUT = 30           # timeout máximo sem receber mensagem (evita half-open)
WS_RECONNECT_DELAY = 5         # segundos entre tentativas de reconexão
WS_FALLBACK_HOSTS = [
    "pvserver:10001",           # hostname DNS local (padrão)
    "localhost:10001",          # mesma máquina
    "127.0.0.1:10001",          # fallback IP local
]

from dotenv import load_dotenv

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
except ImportError:
    openwakeword = None
    OWWModel = None

try:
    import vosk

    vosk.SetLogLevel(-1)
except ImportError:
    vosk = None


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
# Usar logging (não print) garante nível, timestamp e nome do módulo em cada
# linha — essencial para diagnosticar problemas via `journalctl -u
# alfredo-satellite.service -f` sem precisar adivinhar o que aconteceu.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("alfredo.satellite")

# Carrega variáveis do .env (ALFREDO_OWW_THRESHOLD, ALFREDO_SOFTWARE_GAIN etc.)
# ANTES de instanciar AudioConfig, para que os field defaults funcionem.
load_dotenv()

# --------------------------------------------------------------------------
# Configuração / constantes
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AudioConfig:
    rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    blocksize: int = 1280  # OpenWakeWord usa chunks de 1280 samples (80ms) a 16kHz
    wave_output: str = "request.wav"
    wave_response: str = "response.wav"

    # Mantido do original — margem calibrada empiricamente.
    preferred_mic_name: str = field(default_factory=lambda: os.getenv("ALFREDO_MIC_NAME", "PS3 Eye"))

    # Cooldown de playback: evita que o microfone capture o finalzinho da
    # própria fala da caixa de som (modo mãos-livres de sessões).
    # 3.0s porque o buffer ALSA/PulseAudio de computadores antigos (Celeron)
    # pode atrasar a reprodução do ffplay em até 2 segundos.
    playback_tail_cooldown: float = 3.0

    vad_base_cooldown: float = 3.0     # cooldown inicial do VAD-only (segundos)
    vad_max_cooldown: float = 120.0    # cooldown máximo (2 min) se continuar disparando falso

    dashcam_seconds: int = 6           # segundos de pré-gravação mantidos em buffer
    noise_gate_hold_frames: int = 20   # 20 chunks de 20ms = 400ms — preserva consoantes fracas

    # Threshold do OpenWakeWord (0.4 para ambientes ruidosos/TV alta).
    # Mais baixo → mais sensível, mas pode aumentar falsos positivos.
    # Ajustável via .env: ALFREDO_OWW_THRESHOLD=0.35
    oww_threshold: float = field(
        default_factory=lambda: float(os.getenv("ALFREDO_OWW_THRESHOLD", "0.4"))
    )

    # Ganho de software aplicado ANTES do OWW/VAD (não afeta gravação enviada).
    # Ajuda quando o usuário está distante do microfone (sofá x TV).
    # 2.0x é um bom equilíbrio entre captar voz distante e não saturar
    # com o som da TV. Se a TV ficar muito alta, reduzir via .env.
    # Ajustável via .env: ALFREDO_SOFTWARE_GAIN=1.5
    software_gain: float = field(
        default_factory=lambda: float(os.getenv("ALFREDO_SOFTWARE_GAIN", "2.0"))
    )

    server_url: str = field(
        default_factory=lambda: os.getenv("ALFREDO_SERVER_URL", "http://pvserver:10001")
    )
    device_id: str = field(
        default_factory=lambda: os.getenv("ALFREDO_DEVICE_ID", "server-satellite-sala")
    )
    room_id: str = field(
        default_factory=lambda: os.getenv("ALFREDO_ROOM_ID", "ROOM_LIVING")
    )

    @property
    def dashcam_max_bytes(self) -> int:
        return self.dashcam_seconds * self.rate * 2  # 16-bit = 2 bytes/sample


CFG = AudioConfig()

WAKE_WORD_DEFAULT = "alexa"
WAKE_VARIANTS_DEFAULT = ["alfredo", "alfre", "fredo", "al fredo", "alfred", "alexa", "é alexa"]

# --------------------------------------------------------------------------
# Ducking da TV ao ouvir wake word
# --------------------------------------------------------------------------
# O ducking é feito via KEY_MUTE (instantâneo). O volume em si não é
# alterado — apenas o estado mute da TV é togglado. O handler offline
# _handle_volume ('volume no X') usa VOLDOWN/KEY_VOLUP diretamente
# e NÃO conflita com o mute.

# Duração mínima (segundos) antes de desmutar — evita toggle rápido
# em falsos positivos consecutivos.
VOLUME_MIN_DURATION: float = 1.5

# Cool-down mínimo entre mutos consecutivos (segundos) — evita
# falsos positivos de wakeword que poderiam gerar múltiplos mutos
# acidentalmente. Só permite um novo mute se passou este tempo.
MIN_MUTE_COOLDOWN: float = 5.0

# --------------------------------------------------------------------------
# Comandos offline — matching por ação + alvo (com sinônimos), não mais
# frase exata. Cobre muito mais variações de fala ("liga a luz da sala",
# "pode acender a luz da sala", "ativa luz sala"...) com bem menos regras.
# --------------------------------------------------------------------------
ACTION_SYNONYMS_ON = {"liga", "ligar", "acende", "acender", "ativa", "ativar"}
ACTION_SYNONYMS_OFF = {"desliga", "desligar", "apaga", "apagar", "desativa", "desativar"}
ACTION_SYNONYMS_MUTE = {"muta", "mutar", "silencia", "silenciar"}
ACTION_SYNONYMS_UNMUTE = {"desmuta", "desmutar"}
ACTION_SYNONYMS_STOP = {"para", "pare", "pausa", "pausar", "cancela", "cancelar"}

WORD_LIGHT = {"luz", "luzes", "lampada", "lampadas"}
WORD_TV = {"tv", "televisao"}
WORD_VOLUME = {"volume"}  # usado em "volume no 15", "coloca o volume no 8"
WORD_MUSIC = {"musica", "som", "spotify"}
WORD_TIME = {"horas"}  # casa com "que horas são" / "que horas sao"

# Alvos de luz, do mais específico pro mais genérico (checados nessa ordem
# pra "quarto da laura" não cair sem querer no fallback "quarto").
#
# ⚠️ CORREÇÃO: expandido para cobrir mais cômodos. O matching offline via
# Vosk é a camada mais rápida (~50ms). Se não bater aqui, cai no fallback
# do endpoint /api/smart-home/offline do servidor (que resolve pelo BD).
LIGHT_TARGETS: list[tuple[list[str], list[str]]] = [
    (["quarto da laura", "quarto laura"], ["light.luz_quarto_laura"]),
    (["quarto do casal", "quarto casal"], ["light.luz_quarto_casal", "light.luz_quarto_casal_2"]),
    (["sala de jantar", "sala jantar"], ["light.luz_sala_jantar", "light.luz_sala_jantar_2"]),
    (["sala de estar"], ["light.luz_sala", "light.luz_sala_2"]),
    (["sala"], ["light.luz_sala", "light.luz_sala_2"]),
    (["escritorio"], ["light.luz_escritorio"]),
    (["cozinha"], ["light.luz_cozinha"]),
    (["varanda", "sacada"], ["light.luz_varanda"]),
    (["banheiro", "wc"], ["light.luz_banheiro"]),
    (["lavanderia", "area de servico"], ["light.luz_lavanderia"]),
    (["jardim", "quintal"], ["light.luz_jardim"]),
    (["garagem"], ["light.luz_garagem"]),
]

EMERGENCY_SINGLE_WORDS = {"para", "pausa", "chega", "silêncio", "silencio", "desliga"}
EMERGENCY_PHRASES = {"cala a boca"}


def _normalize(text: str) -> str:
    """minúsculas, sem acento, sem pontuação, espaços únicos."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_word(text: str, word_or_phrase: str) -> bool:
    """Casa `word_or_phrase` como palavra/frase inteira (com \\b), não substring solta."""
    return re.search(rf"\b{re.escape(word_or_phrase)}\b", text) is not None


def _has_any(text: str, words) -> bool:
    return any(_has_word(text, w) for w in words)


# --------------------------------------------------------------------------
# Home Assistant helpers (comandos offline / rápidos)
# --------------------------------------------------------------------------
def get_ha_token() -> str:
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
    )
    try:
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("HOME_ASSISTANT_TOKEN="):
                    return line.split("=", 1)[1].strip()
    except OSError as e:
        log.warning("Não foi possível ler HOME_ASSISTANT_TOKEN de %s: %s", env_path, e)
    return ""


def _offline_beep() -> None:
    """Feedback sonoro curto e imediato — confirma que o comando offline
    foi entendido, sem depender do servidor/TTS."""
    try:
        beep_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alarm.wav")
        if os.path.exists(beep_path):
            subprocess.run(["aplay", "-q", beep_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("\a", end="", flush=True)
    except Exception as e:
        log.debug("Falha ao tocar beep offline: %s", e)


SERVER_FALLBACK_URLS = [
    "http://127.0.0.1:10001",
    "http://localhost:10001",
    CFG.server_url,
]

HA_FALLBACK_URLS = [
    "http://pvserver:8123",
    "http://localhost:8123",
    "http://127.0.0.1:8123",
    "http://homeassistant.local:8123",
    "http://192.168.0.1:8123",
]


def _server_request(method: str, path: str, **kwargs) -> requests.Response | None:
    """Faz requisição HTTP ao servidor com fallback automático entre URLs."""
    last_exc = None
    for base_url in SERVER_FALLBACK_URLS:
        url = f"{base_url}{path}"
        try:
            resp = requests.request(method, url, **kwargs)
            resp.raise_for_status()
            log.info("📡 [SERVER] %s %s -> %s via %s", method, path, resp.status_code, base_url)
            return resp
        except requests.RequestException as e:
            last_exc = e
            log.info("📡 [SERVER] %s %s falhou em %s: %s", method, path, base_url, e)
            continue
    log.warning("📡 [SERVER] %s %s inacessível: %s", method, path, last_exc)
    return None


def _ha_call(domain: str, service: str, entity_ids: list[str]) -> None:
    """Chama um serviço do Home Assistant direto (bypassa o servidor/LLM
    inteiro — é isso que dá a latência quase-zero dos comandos offline)."""
    token = get_ha_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for eid in entity_ids:
        sent = False
        for base_url in HA_FALLBACK_URLS:
            url = f"{base_url}/api/services/{domain}/{service}"
            try:
                requests.post(url, headers=headers, json={"entity_id": eid}, timeout=2)
                log.info("⚡ [OFFLINE] %s.%s → %s enviado para %s", domain, service, eid, base_url)
                sent = True
                break
            except requests.RequestException:
                continue
        if not sent:
            log.warning("Erro offline HA (%s): nenhum host respondeu", eid)


def _handle_light(text: str) -> bool:
    if not _has_any(text, WORD_LIGHT):
        log.debug("[DIAG] _handle_light: texto '%s' não contém palavra de luz", text)
        return False
    if _has_any(text, ACTION_SYNONYMS_ON):
        service = "turn_on"
        log.debug("[DIAG] _handle_light: ação LIGAR detectada em '%s'", text)
    elif _has_any(text, ACTION_SYNONYMS_OFF):
        service = "turn_off"
        log.debug("[DIAG] _handle_light: ação DESLIGAR detectada em '%s'", text)
    else:
        log.debug("[DIAG] _handle_light: texto '%s' não tem ação on/off", text)
        return False

    # ── 1. Tentar matching hardcoded (ultra-rápido, sem depender do servidor) ──
    for phrases, entity_ids in LIGHT_TARGETS:
        if any(_has_word(text, p) for p in phrases):
            log.info("⚡ [OFFLINE] Luz '%s' → %s", phrases[0], service)
            threading.Thread(target=_ha_call, args=("light", service, entity_ids), daemon=True).start()
            return True

    # Se chegou aqui, é comando de luz mas o cômodo não está nos targets hardcoded
    log.info("[DIAG] _handle_light: cômodo não identificado em '%s', indo para fallback servidor", text)

    # ── 2. Fallback: chama endpoint offline do servidor (resolve pelo BD) ──
    # Útil para cômodos não mapeados no LIGHT_TARGETS hardcoded. O servidor
    # tem acesso ao banco de dados e ao Home Assistant.
    log.info("⚡ [OFFLINE] Luz (fallback servidor) → %s", service)
    threading.Thread(
        target=_offline_server_call,
        args=(service, CFG.room_id),
        daemon=True,
    ).start()
    return True


def _offline_server_call(action: str, room_id: str) -> None:
    """Chama o endpoint offline do servidor Alfredo para controle de luz.
    O servidor resolve os entity_ids corretos via banco de dados."""
    try:
        url = f"{CFG.server_url}/api/smart-home/offline"
        payload = {
            "action": action,
            "device_type": "light",
            "room_id": room_id,
        }
        resp = requests.post(url, json=payload, timeout=3)
        if resp.status_code == 200:
            log.info("⚡ [OFFLINE] Servidor confirmou: %s", resp.json())
        else:
            log.warning("⚡ [OFFLINE] Servidor retornou %s: %s", resp.status_code, resp.text)
            # Último recurso: tenta ligar/desligar todas as luzes da sala via HA direto
            _ha_call("light", action, [f"light.luz_{room_id.lower().replace('room_', '')}"])
    except requests.RequestException as e:
        log.warning("⚡ [OFFLINE] Servidor offline, tentando HA direto: %s", e)
        # Último recurso: HA direto com entity_id genérico
        room_slug = room_id.lower().replace("room_", "")
        _ha_call("light", action, [f"light.luz_{room_slug}"])


def _tv_control(endpoint: str, params: dict) -> None:
    result = _server_request(
        "POST",
        f"/api/tv/control/{CFG.room_id}/{endpoint}",
        params=params, timeout=8,
    )
    if result is None:
        log.warning("[OFFLINE] TV %s falhou — servidor inacessível", endpoint)
    else:
        log.info("⚡ [OFFLINE] TV %s → OK", endpoint)


def _tv_volume_down() -> None:
    """Muta a TV instantaneamente (KEY_MUTE) ao detectar wake word.

    O volume em si NÃO é alterado — apenas o estado mute toggle.
    O handler _handle_volume ('volume no X') ainda funciona via
    VOLDOWN/VOLUP, mas não conflita com este mute instantâneo.
    """
    s = STATE
    _tv_control("mute", {"state": "true"})
    s.tv_was_muted = True
    # O volume estimado NÃO muda — só o mute toggla.


def _tv_volume_up() -> None:
    """Desmuta a TV (KEY_MUTE) após o processamento do comando."""
    s = STATE
    _tv_control("mute", {"state": "false"})
    s.tv_was_muted = False


def _tv_volume_absolute(target: int) -> None:
    """Ajusta o volume da TV para um valor absoluto (ex: 15).

    Usado pelo handler offline 'volume no X'. Calcula a diferença
    entre o volume estimado atual e o alvo, e envia a quantidade
    necessária de VOLDOWN ou VOLUP — sem bottom-out, sem conflito
    com o servidor.

    NÃO mexe no estado de mute (tv_was_muted) — o mute/desmute
    é independente e controlado pelo ducking via KEY_MUTE.
    """
    s = STATE
    current = s.tv_estimated_volume
    diff = current - target  # positivo = precisa abaixar, negativo = subir
    if diff > 0:
        log.info("📺 Volume absoluto: %d → %d (VOLDOWN × %d)", current, target, diff)
        _tv_control("volume-step", {"direction": "down", "steps": str(diff), "delay": "0.25"})
    elif diff < 0:
        steps = abs(diff)
        log.info("📺 Volume absoluto: %d → %d (VOLUP × %d)", current, target, steps)
        _tv_control("volume-step", {"direction": "up", "steps": str(steps), "delay": "0.25"})
    else:
        log.info("📺 Volume já está em %d, nenhum ajuste necessário.", target)
        return
    s.tv_estimated_volume = target


def _handle_tv(text: str) -> bool:
    if not _has_any(text, WORD_TV):
        return False
    if _has_any(text, ACTION_SYNONYMS_MUTE):
        log.info("⚡ [OFFLINE] Mutando TV")
        threading.Thread(target=_tv_control, args=("mute", {"state": "true"}), daemon=True).start()
        return True
    if _has_any(text, ACTION_SYNONYMS_UNMUTE):
        log.info("⚡ [OFFLINE] Desmutando TV")
        threading.Thread(target=_tv_control, args=("mute", {"state": "false"}), daemon=True).start()
        return True
    if _has_any(text, ACTION_SYNONYMS_ON):
        log.info("⚡ [OFFLINE] Ligando TV")
        threading.Thread(target=_tv_control, args=("power", {"state": "on"}), daemon=True).start()
        return True
    if _has_any(text, ACTION_SYNONYMS_OFF):
        log.info("⚡ [OFFLINE] Desligando TV (comando absoluto, sem toggle)")
        threading.Thread(target=_tv_control, args=("power", {"state": "off"}), daemon=True).start()
        return True
    return False


def _handle_volume(text: str) -> bool:
    """Handler offline para 'volume no 15', 'coloca o volume no 8', etc.

    Extrai o número do texto e ajusta o volume da TV localmente via
    KEY_VOLDOWN/KEY_VOLUP, sem passar pelo servidor/LLM — resposta
    quase instantânea e sem conflito com o ducking do OWW.
    """
    import re
    m = re.search(r'volume\s*(?:no|em|para|deixar\s*em)?\s*(\d{1,3})', _normalize(text))
    if not m:
        return False
    target = int(m.group(1))
    if not (1 <= target <= 100):
        return False
    log.info("⚡ [OFFLINE] Volume absoluto detectado: %d", target)
    threading.Thread(target=_tv_volume_absolute, args=(target,), daemon=True).start()
    return True


def _music_stop() -> None:
    _stop_current_music()
    _server_request("POST", "/api/spotify/control", json={"action": "pause"}, timeout=3)


def _handle_music(text: str) -> bool:
    if not _has_any(text, WORD_MUSIC):
        return False
    if _has_any(text, ACTION_SYNONYMS_STOP):
        log.info("⚡ [OFFLINE] Parando música")
        threading.Thread(target=_music_stop, daemon=True).start()
        return True
    return False


def _speak_offline(text: str) -> None:
    """TTS local mínimo via espeak-ng, só pra respostas curtas (hora).
    Degrada graciosamente se não estiver instalado — não é um substituto
    do TTS do servidor (Edge TTS), só um atalho pra esse caso pontual."""
    try:
        subprocess.run(
            ["espeak-ng", "-v", "pt-br", "-s", "150", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=6, check=True,
        )
    except FileNotFoundError:
        log.warning(
            "⚠️ [OFFLINE] espeak-ng não instalado — resposta de voz local indisponível "
            "(instale com: sudo apt install espeak-ng). Hora calculada: %s", text
        )
    except Exception as e:
        log.warning("⚠️ [OFFLINE] Falha ao falar hora localmente: %s", e)


def _handle_time(text: str) -> bool:
    if not _has_any(text, WORD_TIME):
        return False
    now = datetime.now()
    frase = f"Agora são {now.hour} horas e {now.minute} minutos."
    log.info("⚡ [OFFLINE] Hora solicitada: %s", frase)
    threading.Thread(target=_speak_offline, args=(frase,), daemon=True).start()
    return True


# Ordem importa: mais específico primeiro. Cada handler recebe o texto já
# normalizado e retorna True se tratou o comando (interrompe o pipeline
# normal de STT/LLM pra esse trecho de fala).
_OFFLINE_INTENT_HANDLERS: list[Callable[[str], bool]] = [
    _handle_light,
    _handle_tv,
    _handle_volume,   # "volume no 15" — antes do handler de música
    _handle_music,
    _handle_time,
]


def _check_offline_command(text: str) -> bool:
    normalized = _normalize(text)
    if not normalized:
        return False
    log.debug("[DIAG] _check_offline_command testando: '%s'", normalized)
    for handler in _OFFLINE_INTENT_HANDLERS:
        if handler(normalized):
            log.info("⚡ [OFFLINE] Handler %s executou para: '%s'", handler.__name__, normalized)
            _offline_beep()
            return True
        else:
            log.debug("[DIAG] Handler %s não匹配 para: '%s'", handler.__name__, normalized)
    log.debug("[DIAG] Nenhum handler offline匹配 para: '%s'", normalized)
    return False


# --------------------------------------------------------------------------
# Áudio: descoberta de dispositivo, stream, limpeza de sinal
# --------------------------------------------------------------------------
def find_input_device(name_substring: Optional[str]) -> tuple[Optional[int], int, float]:
    """Procura um dispositivo de entrada com fallback por prioridade."""
    try:
        devices = sd.query_devices()
        preferred_terms = []
        if name_substring:
            preferred_terms.append(name_substring)
        preferred_terms.extend(["omnivision", "ps3 eye", "ps3", "eye", "usb camera"])

        for term in preferred_terms:
            term_lower = term.lower()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0 and term_lower in dev.get("name", "").lower():
                    log.info(
                        "🎙️ [ÁUDIO] Dispositivo preferido encontrado: [%s] %s (%s canais, %sHz)",
                        idx, dev["name"], dev["max_input_channels"], dev.get("default_samplerate"),
                    )
                    return idx, int(dev["max_input_channels"]), float(dev.get("default_samplerate") or CFG.rate)

        for idx, dev in enumerate(devices):
            if dev.get("max_input_channels", 0) > 0:
                log.warning(
                    "⚠️ [ÁUDIO] Usando primeiro input disponível: [%s] %s (%s canais, %sHz)",
                    idx, dev["name"], dev["max_input_channels"], dev.get("default_samplerate"),
                )
                return idx, int(dev["max_input_channels"]), float(dev.get("default_samplerate") or CFG.rate)
    except Exception as e:
        log.error("⚠️ [ÁUDIO] Erro ao buscar dispositivo preferido: %s", e)
    log.warning("⚠️ [ÁUDIO] Nenhum dispositivo de entrada encontrado, usando padrão do sistema.")
    return None, CFG.channels, float(CFG.rate)


def open_input_stream(
    device_index: Optional[int], device_channels: int, samplerate: float, callback
) -> sd.InputStream:
    """Abre o stream tentando a taxa preferida e depois o sample rate nativo do device."""
    attempts: list[float] = []
    preferred_rate = float(CFG.rate)
    native_rate = float(samplerate or CFG.rate)

    for rate in (preferred_rate, native_rate):
        if rate in attempts:
            continue
        attempts.append(rate)
        try:
            log.info("🎚️ [ÁUDIO] Tentando abrir InputStream em %s Hz...", rate)
            return sd.InputStream(
                device=device_index,
                samplerate=rate,
                channels=device_channels,
                dtype=CFG.dtype,
                blocksize=CFG.blocksize,
                callback=callback,
            )
        except Exception as exc:
            log.warning("⚠️ [ÁUDIO] Falha ao abrir stream em %s Hz: %s", rate, exc)

    raise RuntimeError(
        f"Não foi possível abrir nenhum InputStream válido para o device {device_index} "
        f"com taxas testadas: {attempts}"
    )


def _run_audio_mixer_commands(commands: list[list[str]]) -> None:
    """Tenta aplicar comandos de áudio com fallback entre pactl e amixer."""
    for cmd in commands:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception as exc:
            log.warning("⚠️ [ÁUDIO] Falha ao executar %s: %s", " ".join(cmd), exc)


def apply_capture_level(percent: str) -> None:
    _run_audio_mixer_commands([
        ["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{percent}%"],
        ["amixer", "sset", "Capture", f"{percent}%"],
        ["amixer", "-c", "1", "sset", "Mic", f"{percent}%"],
    ])


def apply_master_level(percent: str) -> None:
    _run_audio_mixer_commands([
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
        ["amixer", "sset", "Master", f"{percent}%"],
    ])


_highpass_sos = None  # cache do filtro high-pass (calculado uma vez)


def _get_highpass_filter():
    """Retorna coeficientes SOS do filtro high-pass 80Hz, com cache."""
    global _highpass_sos
    if _highpass_sos is None:
        try:
            from scipy.signal import butter

            _highpass_sos = butter(4, 80, btype="highpass", fs=16000, output="sos")
            log.info("🎛️ [ÁUDIO] Filtro high-pass 80Hz (scipy) ativado.")
        except ImportError:
            log.warning("⚠️ [ÁUDIO] scipy não disponível — filtro high-pass desativado.")
            _highpass_sos = False
    return _highpass_sos


def get_rms(data: bytes) -> float:
    samples = array.array("h", data[: len(data) - (len(data) % 2)])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def is_confirmed_speech(vad_says_speech: bool, rms: float, threshold: float) -> bool:
    """Confirma fala combinando o veredito espectral do WebRTC VAD com a
    energia (RMS) do chunk, usando o `noise_threshold` calibrado no boot.

    BUG CORRIGIDO: antes, vad.is_speech() sozinho decidia se um chunk de
    10ms era "fala". O VAD analisa espectro, não volume — e com o
    microfone USB amplificado 4x por software (SOFTWARE_MULTIPLIER),
    ruído de fundo constante tinha espectro parecido com fala e o VAD
    disparava True quase sem parar. Resultado: silence_frames nunca
    passava do limiar (0.3-0.5s) e TODO comando esperava o teto rígido de
    8s (max_total) antes de ser processado — essa espera "morta" no
    satélite, e não o LLM/TTS no servidor, era a causa real dos ~6s de
    demora reportados.
    """
    return bool(vad_says_speech) and rms > threshold


def clean_audio(samples: np.ndarray, state) -> np.ndarray:
    """Pipeline de limpeza de áudio contínuo: high-pass 80Hz mantendo o estado (zi)."""
    audio = samples.astype(np.float32)

    sos = _get_highpass_filter()
    if sos is not False and sos is not None:
        try:
            from scipy.signal import sosfilt
            import numpy as np

            if not hasattr(state, "audio_filter_zi") or state.audio_filter_zi is None:
                state.audio_filter_zi = np.zeros((sos.shape[0], 2), dtype=np.float32)

            audio, state.audio_filter_zi = sosfilt(sos, audio, zi=state.audio_filter_zi)
            audio = audio.astype(np.float32)
        except Exception:
            audio -= np.mean(audio)
    else:
        audio -= np.mean(audio)

    return audio


def soft_clip(audio: np.ndarray, threshold: float = 28000) -> np.ndarray:
    """Comprime suavemente picos com tanh, evitando os estouros audíveis do hard clip."""
    mask = np.abs(audio) > threshold
    if np.any(mask):
        sign = np.sign(audio[mask])
        excess = np.abs(audio[mask]) - threshold
        max_excess = 32767 - threshold
        compressed = threshold + max_excess * np.tanh(excess / max_excess)
        audio[mask] = sign * compressed
    return audio


# --------------------------------------------------------------------------
# Estado do satélite (agrupa o que antes eram ~25 variáveis globais soltas)
# --------------------------------------------------------------------------
class SatelliteState:
    def __init__(self, cfg: AudioConfig):
        self.cfg = cfg

        self.wake_word = WAKE_WORD_DEFAULT
        self.wake_variants = list(WAKE_VARIANTS_DEFAULT)

        self.alarm_process: Optional[subprocess.Popen] = None
        self.audio_stream: Optional[sd.InputStream] = None
        self.oww_model: Optional[OWWModel] = None
        self.vad: Optional[webrtcvad.Vad] = None
        self.vosk_model = None
        self.vosk_rec = None

        self._last_detection_lock = threading.Lock()

        self._playback_lock = threading.Lock()
        self.is_playing = False
        self.playback_cooldown_until = 0.0

        self._session_lock = threading.Lock()
        self.session_mode = False

        self.vad_only_mode = False
        self.vad_speech_frames = 0

        self.current_music_process: Optional[subprocess.Popen] = None
        self.player_process: Optional[subprocess.Popen] = None

        # Estado de gravação
        self.is_recording = False
        self.has_spoken = False
        self.silence_frames = 0
        self.recording_buffer = bytearray()
        self.full_audio_buffer = bytearray()
        self.dashcam_buffer = bytearray()
        self.accumulated_vosk_text = ""
        self.live_recording_bytes = 0

        # FIX A: rastreia se o satélite MUTOU/ABAIXOU a TV para só restaurar
        # quando necessário (evita unmute espúrio em gravações VAD-only).
        self.tv_was_muted = False

        # Timestamp de quando o volume foi abaixado — usado para garantir
        # uma duração mínima antes de restaurar (VOLUME_MIN_DURATION).
        self.tv_volume_lowered_at: float = 0.0

        # Estimativa local do volume atual da TV — usada pelo handler offline
        # de "volume no X" para calcular quantos VOLDOWN/VOLUP enviar sem
        # precisar de bottom-out (que conflita com o servidor).
        self.tv_estimated_volume: int = 25

        # FIX B: cooldown adaptativo entre gravações do VAD — se disparar
        # repetidamente sem wake word, o cooldown cresce exponencialmente.
        self.vad_consecutive_triggers = 0
        self.vad_last_trigger_time = 0.0

        # Calibração de ruído
        self.is_calibrated = False
        self.calibration_frames = 0
        self.calibration_sum = 0.0
        self.noise_threshold = 2000.0
        self.noise_gate_hold = 0

        self.software_multiplier = self.cfg.software_gain

        self.is_streaming = False
        self.stream_queue: queue.Queue = queue.Queue(maxsize=20)
        self.ws_instance = None
        self._playing_since: float = 0.0

        # Fila produtor-consumidor: audio callback (produtor) descarrega o
        # áudio bruto aqui o mais rápido possível e uma thread separada
        # (consumidora) executa scipy filter + OWW + VAD + gravação. Isso
        # evita buffer overflow (callback lento) e loop infinito no PortAudio.
        self.audio_queue: queue.Queue = queue.Queue(maxsize=60)  # ~4.8s de buffer
        self._audio_worker_stop = threading.Event()

    # -- playback state helpers ------------------------------------------------
    def set_playing(self, value: bool) -> None:
        with self._playback_lock:
            self.is_playing = value
            if value:
                self._playing_since = time.time()

    def set_session_mode(self, value: bool) -> None:
        with self._session_lock:
            self.session_mode = value


STATE = SatelliteState(CFG)


# --------------------------------------------------------------------------
# Alarme
# --------------------------------------------------------------------------
def play_alarm_loop() -> None:
    alarm_file = os.path.join(os.path.dirname(__file__), "alarm.wav")
    if not os.path.exists(alarm_file):
        log.warning("⚠️ Arquivo de alarme não encontrado.")
        return
    stop_alarm()
    log.info("🔔 Despertador tocando!")
    cmd = f"timeout 60 sh -c 'while true; do aplay -q \"{alarm_file}\"; done'"
    STATE.alarm_process = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)


def stop_alarm() -> None:
    if STATE.alarm_process:
        try:
            os.killpg(os.getpgid(STATE.alarm_process.pid), signal.SIGTERM)
        except Exception:
            pass
        STATE.alarm_process = None


# --------------------------------------------------------------------------
# Registro no servidor
# --------------------------------------------------------------------------
def register_device() -> bool:
    log.info("Registrando dispositivo %s no servidor...", CFG.device_id)
    url = f"{CFG.server_url}/api/devices/register"
    payload = {
        "device_id": CFG.device_id,
        "room_id": CFG.room_id,
        "hardware": "linux-server-satellite",
        "firmware_version": "1.0.0",
        "capabilities": ["microphone", "speaker"],
    }
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            log.info("Registro OK! Servidor respondeu: %s", response.json()["message"])
            try:
                settings_res = requests.get(f"{CFG.server_url}/api/dashboard/settings", timeout=3)
                if settings_res.status_code == 200:
                    settings_data = settings_res.json()
                    if "assistant_name" in settings_data:
                        STATE.wake_word = settings_data["assistant_name"].lower()
                        STATE.wake_variants = [STATE.wake_word]
                        log.info("📡 Wake Word sincronizado com o servidor: %s", STATE.wake_word.upper())
            except Exception as e:
                log.warning("Aviso: não foi possível sincronizar o Wake Word: %s", e)
            return True
        except requests.RequestException as e:
            log.warning("Falha ao registrar (tentativa %s/%s): %s", attempt, max_retries, e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return False


# --------------------------------------------------------------------------
# Reprodução de áudio (resposta gravada localmente, não streaming)
# --------------------------------------------------------------------------
def play_audio(filename: str) -> None:
    STATE.set_playing(True)
    log.info("🔊 Reproduzindo resposta (volume amplificado)...")
    try:
        amplified = "response_loud.wav"
        subprocess.run(
            ["sox", filename, amplified, "vol", "3.0"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(["aplay", "-q", amplified], check=True)
    except Exception as e:
        log.warning("Erro ao reproduzir áudio: %s. Tentando sem amplificação...", e)
        try:
            subprocess.run(["aplay", "-q", filename], check=True)
        except Exception as e2:
            log.error("Erro fatal ao reproduzir: %s", e2)
    STATE.set_playing(False)
    STATE.playback_cooldown_until = time.time() + CFG.playback_tail_cooldown


def _stop_current_music() -> None:
    if STATE.current_music_process:
        try:
            STATE.current_music_process.terminate()
            STATE.current_music_process.wait(timeout=2)
        except Exception:
            pass
        STATE.current_music_process = None
    STATE.set_playing(False)


def _watch_music_process(proc: subprocess.Popen) -> None:
    try:
        proc.wait()
    except Exception:
        pass
    if STATE.current_music_process is proc:
        STATE.current_music_process = None
    STATE.set_playing(False)


def send_audio_and_play(filename: str) -> None:
    """Envia um arquivo de áudio via HTTP (fluxo legado, não-WebSocket)."""
    log.info("Enviando áudio para o servidor (Groq API STT e Router)...")
    url = f"{CFG.server_url}/api/voice"
    headers = {
        "X-Device-ID": CFG.device_id,
        "X-Room-ID": CFG.room_id,
        "Authorization": "Bearer mock-token-123",
    }
    try:
        with open(filename, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            start_time = time.time()
            response = requests.post(url, headers=headers, files=files, stream=True)

        if response.status_code == 200:
            first_byte_received = False
            player_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    if not first_byte_received:
                        ttfb = time.time() - start_time
                        log.info("🔊 Áudio iniciado em %.2f segundos!", ttfb)
                        first_byte_received = True
                    player_process.stdin.write(chunk)
                    player_process.stdin.flush()

            player_process.stdin.close()
            player_process.wait()
            total_time = time.time() - start_time
            log.info("✅ Interação concluída. Tempo total: %.2f segundos.", total_time)
        else:
            log.error("Erro do servidor: %s - %s", response.status_code, response.text)
    except Exception as e:
        log.error("Falha na comunicação com o servidor: %s", e)


# --------------------------------------------------------------------------
# Callback de áudio (coração do pipeline: wake word, VAD, gravação)
# --------------------------------------------------------------------------
def audio_callback(indata, frames, time_info, status) -> None:
    try:
        _audio_callback_impl(indata, frames, time_info, status)
    except Exception as e:
        # Nunca deixar uma exceção aqui derrubar o InputStream inteiro —
        # isso é o que causava o crash-loop silencioso do serviço.
        log.error("⚠️ [AUDIO] Erro no callback: %s", e, exc_info=True)


def _is_emergency_stop(candidate_text: str) -> bool:
    """
    FIX: antes usava "in" (substring), o que disparava com QUALQUER frase
    contendo "para" no meio (ex: "isso é para você", "parabéns") — palavras
    comuníssimas em português. Agora exige que o texto reconhecido seja
    CURTO (o usuário disse só o comando) e que a palavra apareça inteira.
    """
    trimmed = candidate_text.strip()
    words = trimmed.split()
    if not words or len(words) > 3:
        return False
    if trimmed in EMERGENCY_PHRASES:
        return True
    return any(w in EMERGENCY_SINGLE_WORDS for w in words)


def _audio_callback_impl(indata, frames, time_info, status) -> None:
    """Produtor RÁPIDO: beamforming + ganho → fila. SEMPRE <1ms."""
    cfg = CFG
    s = STATE

    if status and status.input_overflow:
        log.warning("⚠️ [AUDIO] Buffer overflow detectado! Áudio pode picotar.")

    # Beamforming: se o dispositivo tem mais de 1 canal (ex: array de 4 mics
    # da PS3 Eye), faz média de TODOS os canais — cancela ruído
    # não-correlacionado e reforça a voz, melhorando SNR em ~6dB.
    if indata.ndim > 1 and indata.shape[1] > 1:
        flattened = np.mean(indata, axis=1)
    else:
        flattened = indata.flatten()

    # Ganho de software (pré-clipping, SEM scipy filter aqui)
    if s.software_multiplier != 1.0:
        flattened = flattened * s.software_multiplier

    # soft_clip + conversão para int16
    bytes_data = soft_clip(flattened).astype(np.int16).tobytes()

    # Empurra para a fila de processamento (non-blocking, descarta se cheia)
    try:
        s.audio_queue.put_nowait(bytes_data)
    except queue.Full:
        # Se a fila encheu, o processamento está atrasado. Descarta o mais
        # antigo para manter latência baixa.
        try:
            s.audio_queue.get_nowait()
            s.audio_queue.put_nowait(bytes_data)
        except queue.Empty:
            pass


def _audio_processing_worker() -> None:
    """Consumidor: lê da fila de áudio e executa scipy filter + OWW + VAD + gravação.

    Roda em uma thread separada (daemon) para não travar o callback de áudio.
    """
    cfg = CFG
    s = STATE
    log.info("🎛️ [WORKER] Iniciado thread de processamento de áudio")

    while not s._audio_worker_stop.is_set():
        try:
            bytes_data = s.audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        # ── scipy high-pass filter ──────────────────────────────────────────
        # O scipy filter é a operação mais pesada; está aqui no worker, não no
        # callback, para não causar buffer overflow.
        float32_data = np.frombuffer(bytes_data, dtype=np.int16).astype(np.float32)
        cleaned = clean_audio(float32_data, s)
        bytes_data = cleaned.astype(np.int16).tobytes()

        # ── Encaminha para o stream ao vivo (Dashboard) ────────────────────
        if s.is_streaming:
            try:
                s.stream_queue.put_nowait(bytes_data)
            except queue.Full:
                try:
                    s.stream_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    s.stream_queue.put_nowait(bytes_data)
                except queue.Full:
                    pass

        # ── Calibração inicial (~2s para ler o ruído do ambiente) ──────────
        if not s.is_calibrated:
            rms = get_rms(bytes_data)
            s.calibration_sum += rms
            s.calibration_frames += 1
            required_frames = int((cfg.rate / cfg.blocksize) * 2.0)

            if s.calibration_frames >= required_frames:
                avg_noise = s.calibration_sum / s.calibration_frames
                # Multiplicador 3.5x: margem ampla para ignorar TV/rádio de fundo.
                # Se a TV estiver ligada durante a calibração, o noise floor já
                # inclui o áudio ambiente; com 3.5x evitamos falso-positivos.
                s.noise_threshold = avg_noise * 3.5 + 100
                log.info("🎙️ [CALIBRAÇÃO] Ruído de fundo médio: %.1f", avg_noise)
                log.info("🎙️ [CALIBRAÇÃO] Noise Threshold dinâmico definido para: %.1f", s.noise_threshold)
                s.is_calibrated = True
            continue

        # ── Safety net: is_playing travado ────────────────────────────────
        if s.is_playing and s._playing_since + 30 < time.time() and not s.player_process:
            log.warning(
                "⚠️ [SAFETY] is_playing travado há >30s sem player_process "
                "— forçando reset"
            )
            s.set_playing(False)

        # ── OpenWakeWord (gatilho principal) ────────────────────────────────
        if s.oww_model:
            if s.is_playing or time.time() < s.playback_cooldown_until:
                s.oww_model.reset()
            else:
                prediction = s.oww_model.predict(cleaned)
                for mdl_name, score in prediction.items():
                    if score >= cfg.oww_threshold:
                        current_time = time.time()
                        last_wake_time = getattr(s, 'last_wake_time', 0)
                        if (current_time - last_wake_time) > MIN_MUTE_COOLDOWN:
                            s.last_wake_time = current_time
                            if s.is_recording:
                                if not s.tv_was_muted:
                                    s.tv_was_muted = True
                                    s.tv_volume_lowered_at = time.time()
                                    log.info("🔊 OWW score %.2f — re-trigger, abaixando volume TV", score)
                                    threading.Thread(
                                        target=_tv_volume_down,
                                        daemon=True,
                                    ).start()
                            else:
                                log.info("🔊 OWW score %.2f — iniciando gravação", score)
                                _stop_current_music()
                                s.tv_was_muted = True
                                s.tv_volume_lowered_at = time.time()
                                s.vad_consecutive_triggers = 0
                                threading.Thread(
                                    target=_tv_volume_down,
                                    daemon=True,
                                ).start()
                                _start_recording()
                        break

        # ── VAD-only: fala sustentada dispara gravação ─────────────────────
        if s.vad_only_mode and not s.is_recording:
            if s.is_playing or time.time() < s.playback_cooldown_until:
                s.vad_speech_frames = 0
            else:
                offset = 0
                while offset + 320 <= len(bytes_data):
                    chunk = bytes_data[offset:offset + 320]
                    offset += 320
                    rms = get_rms(chunk)
                    vad_result = s.vad.is_speech(chunk, cfg.rate)
                    if is_confirmed_speech(vad_result, rms, s.noise_threshold):
                        s.vad_speech_frames += 1
                    else:
                        s.vad_speech_frames = 0

                if s.vad_speech_frames >= 8:
                    now = time.time()
                    elapsed_since_last = now - s.vad_last_trigger_time
                    required_cooldown = min(
                        cfg.vad_base_cooldown * (2 ** s.vad_consecutive_triggers), cfg.vad_max_cooldown
                    )
                    if elapsed_since_last < required_cooldown:
                        s.vad_speech_frames = 0
                    else:
                        s.vad_consecutive_triggers += 1
                        s.vad_last_trigger_time = now
                        s.tv_was_muted = False
                        log.info("🔊 [VAD] Fala detectada! Gravando...")
                        _stop_current_music()
                        _start_recording()
                        s.vad_speech_frames = 0

        # ── Dashcam (buffer de áudio pré-wake word) ────────────────────────
        if not s.is_recording:
            if not s.is_playing and time.time() >= s.playback_cooldown_until:
                s.dashcam_buffer.extend(bytes_data)
                if len(s.dashcam_buffer) > cfg.dashcam_max_bytes:
                    del s.dashcam_buffer[:-cfg.dashcam_max_bytes]

        # ── Gravação (Vosk + VAD + detecção de silêncio) ──────────────────
        if s.is_recording:
            _process_recording_chunk(bytes_data)


def _process_recording_chunk(bytes_data: bytes) -> None:
    cfg = CFG
    s = STATE

    s.recording_buffer.extend(bytes_data)
    s.full_audio_buffer.extend(bytes_data)
    s.live_recording_bytes += len(bytes_data)

    if s.vosk_rec:
        if s.vosk_rec.AcceptWaveform(bytes_data):
            res = json.loads(s.vosk_rec.Result())
            text = res.get("text", "")
            if text:
                s.accumulated_vosk_text += " " + text
                log.info("🧠 [VOSK] Texto final: '%s' (acumulado: '%s')", text, s.accumulated_vosk_text.strip())
                if _check_offline_command(s.accumulated_vosk_text):
                    _finish_recording(cancel=True)
                    return
        else:
            res = json.loads(s.vosk_rec.PartialResult())
            partial = res.get("partial", "")
            if partial:
                log.info("🧠 [VOSK] Parcial: '%s'", partial)
                if _check_offline_command(partial):
                    _finish_recording(cancel=True)
                    return

    if s.vosk_rec and _is_emergency_stop(s.accumulated_vosk_text):
        log.info("🛑 Comando de emergência detectado! Abortando.")
        _finish_recording(cancel=True)
        return

    offset = 0
    while offset + 320 <= len(s.recording_buffer):
        chunk = s.recording_buffer[offset:offset + 320]
        offset += 320
        vad_raw_result = s.vad.is_speech(chunk, cfg.rate)
        rms = get_rms(chunk)

        # BUG CORRIGIDO: exige VAD + energia acima do ruído calibrado no
        # boot para considerar "fala real" (ver is_confirmed_speech acima).
        is_speech = is_confirmed_speech(vad_raw_result, rms, s.noise_threshold)

        if is_speech:
            s.noise_gate_hold = cfg.noise_gate_hold_frames
        else:
            if s.noise_gate_hold > 0:
                s.noise_gate_hold -= 1
                is_speech = True  # bridge de consoantes fracas

        if is_speech:
            if not s.has_spoken:
                s.has_spoken = True
                s.silence_frames = 0
            else:
                s.silence_frames = 0
        elif s.has_spoken:
            s.silence_frames += 1

    s.recording_buffer = bytearray(s.recording_buffer[offset:])

    total_frames = len(s.full_audio_buffer) // 320
    # live_frames conta só o áudio capturado desde o início desta gravação,
    # SEM o preload do dashcam — teto de "tempo máximo" com significado consistente.
    live_frames = s.live_recording_bytes // 320

    # ── VAD Adaptativo: corte de silêncio baseado na duração da fala ──────────
    # Quanto mais longa a fala, mais tempo de pausa natural permitimos.
    # live_frames = frames capturados DESTA gravação (sem o dashcam buffer).
    #
    # Nível 1 (< 0.5s de fala): corte rápido em 400ms — "liga a luz" não tem pausa.
    # Nível 2 (0.5-2s):  pausa natural de 600ms — frases médias.
    # Nível 3 (2-5s):    pausa de 800ms — perguntas mais longas.
    # Nível 4 (> 5s):    pausa de 1.0s — relatos longos (quiz, receitas).
    # Ganho vs antes (1.5-2.0s fixo): economiza 600ms a 1.4s por interação.
    if not s.has_spoken:
        # Nunca falou ainda — timeout longo para quem demorou a começar
        max_silence = int(4.0 * cfg.rate / 160)  # 4s sem fala = cancela
    else:
        # Fixo agressivo de 500ms para reduzir latência
        max_silence = int(0.5 * cfg.rate / 160)
    timeout_frames = int(20 * cfg.rate / 160) if s.session_mode else int(5 * cfg.rate / 160)
    max_total = int(8 * cfg.rate / 160)  # 8s máximo de fala nova

    if s.has_spoken and s.silence_frames > max_silence:
        log.info("⏹️ Silêncio detectado. Fim da gravação.")
        _finish_recording()
    elif not s.has_spoken and total_frames > timeout_frames:
        if s.session_mode:
            s.set_session_mode(False)
            log.info("⏳ Ninguém respondeu. Saindo do modo mãos-livres.")
        else:
            log.info("⏳ Ninguém falou nada (5s). Cancelando gravação.")
        s.is_recording = False
        s.recording_buffer.clear()
    elif live_frames > max_total:
        log.info("⏳ Tempo máximo atingido (comando muito longo).")
        _finish_recording()


def _start_recording() -> None:
    s = STATE
    s.is_recording = True
    s.recording_buffer = bytearray()
    s.live_recording_bytes = 0
    s.vad_speech_frames = 0
    s.accumulated_vosk_text = ""

    if s.vosk_model:
        s.vosk_rec = vosk.KaldiRecognizer(s.vosk_model, CFG.rate)

    s.full_audio_buffer = bytearray(s.dashcam_buffer)
    s.dashcam_buffer.clear()

    # BUG CORRIGIDO: antes era `not s.session_mode`, o que marcava
    # has_spoken=True fora do modo mãos-livres. Isso fazia o VAD
    # cortar a gravação em 400ms de silêncio — o usuário falava
    # "alexa" e o sistema nunca esperava o comando de verdade.
    # Agora sempre começamos com False: o VAD dá 4s para o usuário
    # começar a falar, e só depois aplica os thresholds adaptativos.
    s.has_spoken = False
    s.silence_frames = 0
    stop_alarm()

    # ── VAD mode 2 durante gravação ────────────────────────────────────────────
    # Mode 2 é mais agressivo na detecção de silêncio → corta mais rápido.
    # Mode 1 (sensível) é mantido fora de gravação para não perder wake words.
    if s.vad:
        s.vad.set_mode(2)
        log.debug("VAD: modo 2 (agressivo) ativado para gravação")

    if s.session_mode:
        log.info("🔴 [MODO MÃOS-LIVRES] Aguardando resposta (sem wake word)...")
    else:
        log.info("🔴 [GRAVANDO COM DASHCAM] Ouvindo comando (incluindo o passado)...")


def _finish_recording(cancel: bool = False) -> None:
    s = STATE
    s.is_recording = False
    buf = bytes(s.full_audio_buffer)
    s.recording_buffer.clear()
    s.full_audio_buffer.clear()
    s.vosk_rec = None

    # ── VAD volta ao mode 1 (sensível) após a gravação ─────────────────────────
    # Garante que o OWW / VAD-only detection continua funcionando entre interações.
    if s.vad:
        s.vad.set_mode(1)
        log.debug("VAD: modo 1 (sensível) restaurado pós-gravação")

    s.playback_cooldown_until = time.time() + 3.0
    if s.oww_model:
        try:
            s.oww_model.reset()
        except Exception:
            pass

    if cancel:
        log.info("🛑 Gravação cancelada (comando offline executado).")
        return

    live_seconds = s.live_recording_bytes / (CFG.rate * 2)
    log.info("🎙️ [DURAÇÃO] Áudio novo desde o início da gravação: %.2fs", live_seconds)

    if len(buf) < 3200:
        log.info("Áudio muito curto, ignorando.")
        return

    vosk_text = s.accumulated_vosk_text.strip()
    log.info("⏹️ [VAD] Tamanho do áudio: %s bytes. Enviando...", len(buf))
    threading.Thread(target=_send_and_play, args=(buf, vosk_text), daemon=True).start()


def _check_session_mode() -> None:
    s = STATE
    try:
        status_resp = _server_request(
            "GET", "/api/session-status",
            params={"room_id": CFG.room_id}, timeout=2,
        )
        if status_resp and status_resp.status_code == 200 and status_resp.json().get("active") and not s.is_recording:
            s.set_session_mode(True)
            log.info("🎯 Sessão ativa — modo mãos-livres ativado!")
            _start_recording()
        else:
            s.set_session_mode(False)
    except Exception:
        s.set_session_mode(False)


class _SoundDevicePlayer:
    """Reprodução via sounddevice (PortAudio). Player principal no Android/Termux.

    Bufferiza todo o áudio recebido até EOF (stdin fechado), então:
      1. Detecta se é MP3 (sync word 0xFF 0xFx)
      2. Se MP3: decodifica via mpg123 (--stdout) ou pydub
      3. Se PCM: toca direto como int16 48kHz mono
      4. Reproduz via RawOutputStream do sounddevice (PortAudio)

    Simula interface de subprocess.Popen:
      - `stdin` (writeable) — escreva bytes de áudio (MP3 ou PCM)
      - `poll()` / `wait(timeout)` / `kill()`
    """

    def __init__(self):
        self._read_fd, self._write_fd = os.pipe()
        self.stdin = open(self._write_fd, "wb", buffering=0)
        self._closed = False
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()

    def _play_loop(self):
        """Lê todo o pipe, decodifica se MP3, reproduz via sounddevice."""
        try:
            import shutil
            import sounddevice as sd

            _HAS_MPG123 = shutil.which("mpg123") is not None
            try:
                from pydub import AudioSegment
                import io as _io
                _HAS_PYDUB = True
            except ImportError:
                _HAS_PYDUB = False

            # ── Bufferiza TODOS os dados até EOF ────────────────────────────
            buf = bytearray()
            while True:
                chunk = os.read(self._read_fd, 8192)
                if not chunk:
                    break
                buf.extend(chunk)

            if not buf:
                log.debug("[SoundDevicePlayer] Buffer vazio, nada a tocar")
                return

            # ── Detecta MP3 pelo sync word ──────────────────────────────────
            _is_mp3 = len(buf) >= 2 and buf[0] == 0xFF and (buf[1] & 0xE0) == 0xE0
            total_bytes = len(buf)

            if _is_mp3:
                log.info("[SoundDevicePlayer] Decodificando MP3 (%d bytes)...", total_bytes)
                pcm: bytes | None = None

                if _HAS_MPG123:
                    pcm = self._decode_via_mpg123(bytes(buf))
                if pcm is None and _HAS_PYDUB:
                    pcm = self._decode_via_pydub(bytes(buf))
                if pcm is None:
                    log.warning("[SoundDevicePlayer] Não foi possível decodificar MP3 — sem saída")
                    return

                log.info("[SoundDevicePlayer] PCM decodificado: %d bytes", len(pcm))
            else:
                # PCM cru assume-se 48kHz mono int16
                log.info("[SoundDevicePlayer] Reproduzindo PCM cru (%d bytes, 48kHz 16bit mono)...", total_bytes)
                pcm = bytes(buf)

            # ── Reproduz via sounddevice ────────────────────────────────────
            with sd.RawOutputStream(
                samplerate=48000, channels=1, dtype="int16",
            ) as stream:
                # Escreve em blocos de 4096 para não travar o callback
                offset = 0
                while offset < len(pcm):
                    chunk_size = min(4096, len(pcm) - offset)
                    stream.write(pcm[offset:offset + chunk_size])
                    offset += chunk_size

            log.info("[SoundDevicePlayer] Playback concluído (%d bytes PCM)", len(pcm))

        except Exception:
            log.exception("Erro no _SoundDevicePlayer._play_loop")
        finally:
            try:
                os.close(self._read_fd)
            except OSError:
                pass

    @staticmethod
    def _decode_via_mpg123(data: bytes) -> bytes | None:
        """Decodifica MP3 → PCM 48kHz via mpg123 (stdin → stdout).

        Usa `-r 48000` para resample obrigatório: o Edge TTS gera MP3 em
        22050Hz, e tocar PCM 22050Hz como se fosse 48000Hz acelera a voz.
        """
        try:
            proc = subprocess.Popen(
                ["mpg123", "-q", "--stdout", "-r", "48000", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            pcm, _ = proc.communicate(data, timeout=30)
            return pcm
        except Exception as e:
            log.warning("Decodificação mpg123 falhou: %s", e)
            return None

    @staticmethod
    def _decode_via_pydub(data: bytes) -> bytes | None:
        """Decodifica MP3 → PCM 48kHz mono via pydub."""
        try:
            from pydub import AudioSegment
            import io as _io
            seg = AudioSegment.from_mp3(_io.BytesIO(data))
            seg = seg.set_frame_rate(48000).set_channels(1)
            return seg.raw_data
        except Exception as e:
            log.warning("Decodificação pydub falhou: %s", e)
            return None

    def poll(self):
        return -1 if self._closed else None

    def wait(self, timeout=None):
        self._thread.join(timeout=timeout)
        return 0

    def kill(self):
        self._closed = True
        try:
            self.stdin.close()
        except OSError:
            pass


def _start_playback() -> None:
    s = STATE
    s.set_playing(True)
    if s.player_process:
        try:
            s.player_process.stdin.close()
            s.player_process.terminate()
        except Exception:
            pass
    import shutil
    # ── SoundDevicePlayer (PortAudio): player principal ───────────────────────
    # Usa sounddevice (PortAudio) que funciona no Android (OpenSL ES) e Windows
    # (WASAPI). Decodifica MP3 via mpg123 --stdout ou pydub, depois toca PCM.
    # Preferido sobre mpg123 direto porque o driver de saída do mpg123 pode não
    # funcionar no Termux (ALSA quebrado no Android).
    _has_sd = True
    # ── ffplay: apenas quando não tem mpg123 no sistema (Windows/Linux) ───────
    if not shutil.which("mpg123") and shutil.which("ffplay"):
        log.info("▶️ Iniciando playback via ffplay")
        s.player_process = subprocess.Popen(
            [
                "ffplay", "-nodisp", "-autoexit",
                "-fflags", "nobuffer",
                "-flags", "low_delay",
                "-probesize", "32",
                "-analyzeduration", "0",
                "-vn",
                "-i", "pipe:0",
            ],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        log.info("▶️ Iniciando playback via SoundDevicePlayer")
        s.player_process = _SoundDevicePlayer()


def _stop_playback() -> None:
    s = STATE
    if s.player_process:
        try:
            s.player_process.stdin.close()
        except Exception:
            pass
        try:
            s.player_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            log.warning("Player não finalizou em 3s — forçando kill")
            try:
                s.player_process.kill()
            except Exception:
                pass
            s.player_process.wait(timeout=1)
        except Exception:
            pass
        s.player_process = None
    s.set_playing(False)
    s.playback_cooldown_until = time.time() + CFG.playback_tail_cooldown
    threading.Thread(target=_post_playback_cleanup, daemon=True).start()


def _post_playback_cleanup() -> None:
    s = STATE
    # Só restaura o volume se o satélite realmente o abaixou antes (FIX A).
    # Além disso, respeita VOLUME_MIN_DURATION — se o tempo mínimo não
    # tiver passado, espera mais um pouco para evitar toggle rápido.
    if s.tv_was_muted:
        elapsed = time.time() - s.tv_volume_lowered_at
        if elapsed < VOLUME_MIN_DURATION:
            remaining = VOLUME_MIN_DURATION - elapsed
            log.info("⏳ Aguardando %.1fs para restaurar volume (min %.0fs)",
                      remaining, VOLUME_MIN_DURATION)
            time.sleep(remaining)
        _tv_volume_up()
        s.tv_was_muted = False
    time.sleep(CFG.playback_tail_cooldown)
    _check_session_mode()


def _send_and_play(audio_data: bytes, vosk_text: str = "") -> None:
    s = STATE
    ws = s.ws_instance
    if not ws:
        log.error("[RESILIENTE] WebSocket não conectado — áudio será descartado. "
                   "Se a internet/acesso ao servidor cair, o sistema tentará "
                   "reconectar automaticamente a cada %ds com fallback de hosts.",
                   WS_RECONNECT_DELAY)
        return
    try:
        if vosk_text:
            log.info("Enviando texto pré-transcrito: '%s'", vosk_text)
            ws.send(json.dumps({"vosk_text": vosk_text}))
        log.info("Enviando %s bytes via WebSocket...", len(audio_data))
        ws.send(audio_data)
    except Exception as e:
        log.error("Erro ao enviar áudio pelo WebSocket: %s", e)
        # Marca ws_instance como None para forçar reconexão
        s.ws_instance = None


def stream_worker() -> None:
    s = STATE
    while True:
        try:
            data = s.stream_queue.get(timeout=1)
            if s.ws_instance and s.is_streaming:
                try:
                    s.ws_instance.send(data)
                except Exception:
                    pass
        except queue.Empty:
            continue


# --------------------------------------------------------------------------
# WebSocket: canal de comando/controle com o servidor
# --------------------------------------------------------------------------
_WS_HANDLERS = {}


def _ws_handler(msg_type: str):
    def deco(fn):
        _WS_HANDLERS[msg_type] = fn
        return fn
    return deco


@_ws_handler("tts_end")
def _on_tts_end(data: dict) -> None:
    _stop_playback()


@_ws_handler("timer_expired")
def _on_timer_expired(data: dict) -> None:
    log.info("🚨 BIP BIP BIP! ⏰ %s (Duração: %ss)", data.get("message"), data.get("duration_seconds"))


@_ws_handler("play_alarm")
def _on_play_alarm(data: dict) -> None:
    log.info("🚨 [ALARME] %s 🚨", data.get("message", "Despertador tocando!"))
    play_alarm_loop()


@_ws_handler("weather_update")
def _on_weather_update(data: dict) -> None:
    log.info("☁️ [DISPLAY] Clima atualizado: %s", data.get("data"))


@_ws_handler("update_wake_word")
def _on_update_wake_word(data: dict) -> None:
    s = STATE
    s.wake_word = data.get("wake_word", s.wake_word).lower()
    s.wake_variants = [s.wake_word]
    log.info("🔥 [ATUALIZAÇÃO EM TEMPO REAL] Novo Wake Word: %s 🔥", s.wake_word.upper())
    log.info("👉 Diga '%s' para me chamar!", s.wake_word.upper())


@_ws_handler("play_audio")
def _on_play_audio(data: dict) -> None:
    s = STATE
    audio_url = data.get("url")
    log.info("🎵 [SATÉLITE] Comando de tocar stream (live/música): %s", audio_url)
    _stop_current_music()
    try:
        s.current_music_process = subprocess.Popen(
            ["mplayer", "-novideo", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        try:
            s.current_music_process = subprocess.Popen(
                ["cvlc", "--no-video", audio_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            log.error("⚠️ Nenhum player de áudio instalado. Instale: sudo apt install mplayer")
            return
    if s.current_music_process:
        s.set_playing(True)
        threading.Thread(target=_watch_music_process, args=(s.current_music_process,), daemon=True).start()


@_ws_handler("stop_audio")
def _on_stop_audio(data: dict) -> None:
    log.info("🛑 [SATÉLITE] Parando música atual.")
    _stop_current_music()


@_ws_handler("START_STREAM")
def _on_start_stream(data: dict) -> None:
    log.info("🎙️ [LIVE AUDIO] Iniciando stream de áudio ao vivo para o Dashboard...")
    STATE.is_streaming = True


@_ws_handler("STOP_STREAM")
def _on_stop_stream(data: dict) -> None:
    log.info("🛑 [LIVE AUDIO] Parando stream de áudio ao vivo.")
    STATE.is_streaming = False


@_ws_handler("SET_ALSA_CAPTURE")
def _on_set_alsa_capture(data: dict) -> None:
    val = data.get("value")
    log.info("🎚️ Ajustando ALSA Capture para %s%%", val)
    apply_capture_level(f"{int(float(val))}")


@_ws_handler("SET_ALSA_MASTER")
def _on_set_alsa_master(data: dict) -> None:
    val = data.get("value")
    log.info("🔊 Ajustando ALSA Master para %s%%", val)
    apply_master_level(f"{int(float(val))}")


@_ws_handler("SET_SOFTWARE_PREAMP")
def _on_set_software_preamp(data: dict) -> None:
    val = float(data.get("value", 1.0))
    log.info("⚡ Ajustando Multiplicador de Software para %sx", val)
    STATE.software_multiplier = val


def _reset_audio_state() -> None:
    """Reseta flags de áudio/gravação que podem ficar presas após desconexão.

    Chamado sempre que o WebSocket perde a conexão. Previne o deadlock:
    is_playing=True → OWW resetado → wake word nunca detectado → Alexa "morta".
    """
    s = STATE

    # Mata player ffplay se estiver preso
    if s.player_process:
        try:
            s.player_process.stdin.close()
            s.player_process.kill()
            s.player_process.wait(timeout=2)
        except Exception:
            pass
        s.player_process = None

    # Limpa flags e cooldowns — permite wake word voltar a funcionar
    s.set_playing(False)
    s.playback_cooldown_until = 0.0

    # Se estava gravando (deadlock raro), cancela
    if s.is_recording:
        s.is_recording = False
        s.recording_buffer.clear()
        s.full_audio_buffer.clear()
        s.vosk_rec = None

    # Reseta OWW model para evitar estado corrompido
    if s.oww_model:
        try:
            s.oww_model.reset()
        except Exception:
            pass

    log.info("🔄 Estado de áudio resetado após desconexão")


def _build_ws_urls() -> list[str]:
    """Gera lista de URLs de WebSocket em ordem de preferência (fallback)."""
    base_path = f"/api/ws/satellite/{CFG.device_id}"
    original_host = CFG.server_url.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
    original_port = "10001"

    if ":" in CFG.server_url.replace("http://", "").replace("https://", "").split("/")[0]:
        parts = CFG.server_url.replace("http://", "").replace("https://", "").split("/")[0].split(":")
        original_host = parts[0]
        original_port = parts[1] if len(parts) > 1 else "10001"

    seen = set()
    urls = []
    for host in [original_host, *WS_FALLBACK_HOSTS]:
        resolved_host = host.split(":")[0]
        resolved_port = host.split(":")[1] if ":" in host else original_port
        url = f"ws://{resolved_host}:{resolved_port}{base_path}"
        if url not in seen:
            seen.add(url)
            urls.append((resolved_host, url))
    return urls


def websocket_loop() -> None:
    s = STATE
    fallback_urls = _build_ws_urls()
    fallback_index = 0

    # Resolve DNS dos hosts periodicamente (a cada 60s) para pegar mudanças
    # após a internet/quedas de rede voltarem.
    last_dns_refresh = 0.0
    DNS_REFRESH_INTERVAL = 60.0

    while True:
        _host, ws_url = fallback_urls[fallback_index]
        try:
            # Re-resolve DNS periodicamente para pegar mudanças de IP
            now = time.time()
            if now - last_dns_refresh > DNS_REFRESH_INTERVAL:
                last_dns_refresh = now
                try:
                    resolved = socket.getaddrinfo(_host, 10001, socket.AF_INET, socket.SOCK_STREAM)
                    log.debug("[DNS] %s resolvido para %s", _host, resolved[0][4][0])
                except socket.gaierror:
                    log.warning("[DNS] Não foi possível resolver %s — tentando fallback", _host)

            log.info("🔄 Tentando conectar ao WebSocket em %s...", ws_url)
            with connect(ws_url, open_timeout=WS_CONNECT_TIMEOUT) as websocket:
                s.ws_instance = websocket
                fallback_index = 0  # Reset para o primary na próxima reconexão
                log.info("✅ WebSocket conectado com sucesso!")
                while True:
                    try:
                        message = websocket.recv(timeout=WS_RECV_TIMEOUT)
                    except TimeoutError:
                        # Nenhuma mensagem em 30s — envia ping implícito e continua
                        # O próprio timeout já serve como health check: se a conexão
                        # estiver morta, o recv() levantará outra exceção na próxima
                        # tentativa, saindo do loop interno.
                        log.debug("[WS] Timeout sem mensagens — conexão ainda ativa")
                        continue

                    if isinstance(message, bytes):
                        log.info("📥 [TTS] Recebidos %d bytes de áudio do servidor", len(message))
                        if not s.player_process:
                            _start_playback()
                        if s.player_process:
                            s.player_process.stdin.write(message)
                            s.player_process.stdin.flush()
                        continue

                    data = json.loads(message)
                    handler = _WS_HANDLERS.get(data.get("type"))
                    if handler:
                        handler(data)
                    else:
                        log.debug("Mensagem WS sem handler: %s", data.get("type"))
        except (OSError, ConnectionError, TimeoutError) as e:
            # ── Limpeza de estado ao perder conexão ──────────────────────────
            # Impede deadlock: is_playing/is_recording presos em True após queda
            # de rede, o que desabilita a detecção de wake word para sempre.
            log.warning(
                "[WebSocket] Falha ao conectar/manter (%s): %s. "
                "Tentando fallback em %ds...",
                ws_url, e, WS_RECONNECT_DELAY,
            )
            _reset_audio_state()
            s.ws_instance = None
            # Próxima tentativa: fallback para outro host
            fallback_index = (fallback_index + 1) % len(fallback_urls)
            time.sleep(WS_RECONNECT_DELAY)
        except Exception as e:
            log.warning(
                "[WebSocket] Erro inesperado: %s. Reconectando em %ds...",
                e, WS_RECONNECT_DELAY,
            )
            _reset_audio_state()
            s.ws_instance = None
            time.sleep(WS_RECONNECT_DELAY)


# --------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------
def _load_vosk() -> None:
    if not vosk:
        return
    try:
        log.info("🧠 Carregando Vosk (reconhecimento offline)...")
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            # TROCAdo para modelo FULL (~840MB) — small (~40MB) errava
            # metade dos comandos de luz ("apaga" virava "a", "liga" virava "a").
            "core", "voice", "stt", "models", "vosk-model-pt-fb-v0.1.1-20220516_2113",
        )
        if os.path.exists(model_path):
            STATE.vosk_model = vosk.Model(model_path)
            log.info("🟢 Vosk carregado!")
        else:
            log.warning("⚠️ Modelo Vosk não encontrado em %s", model_path)
    except Exception as e:
        log.error("⚠️ Falha ao carregar Vosk: %s", e)


def _load_openwakeword() -> None:
    if openwakeword is None:
        log.warning("⚠️ OpenWakeWord não instalado (pip install openwakeword).")
        STATE.oww_model = None
        return
    log.info("🧠 Carregando OpenWakeWord (gatilho principal)...")
    try:
        paths = openwakeword.get_pretrained_model_paths()
        alexa_path = next((p for p in paths if "alexa" in p), None)
        if alexa_path:
            STATE.oww_model = OWWModel(wakeword_model_paths=[alexa_path])
            log.info("🟢 OpenWakeWord carregado!")
        else:
            log.warning("⚠️ Modelo alexa não encontrado.")
    except Exception as e:
        log.error("⚠️ Falha ao carregar OpenWakeWord: %s", e)
        STATE.oww_model = None


def main() -> None:
    warnings.filterwarnings("ignore")

    _load_vosk()
    _load_openwakeword()

    # VAD-only mode: se o OpenWakeWord não estiver disponível (ex: ARM/Termux
    # sem onnxruntime), ativa o modo VAD-only como fallback. A detecção de
    # fala será feita por energia (VAD + RMS threshold).
    if STATE.oww_model is None:
        STATE.vad_only_mode = True
        log.info("🎤 OpenWakeWord não disponível — modo VAD-only ativado como fallback.")
        log.info("   A detecção de fala será feita por energia (VAD + noise threshold).")
    else:
        STATE.vad_only_mode = False
        log.info("🎤 Modo VAD passivo desativado — apenas OpenWakeWord ('alexa') ativa gravação.")
        log.info("   Sessões interativas (mãos-livres) continuam funcionando normalmente.")

    # Agressividade baixa (1) — mais sensível a voz distante. Ainda
    # necessário para detecção de silêncio durante gravações ativas.
    STATE.vad = webrtcvad.Vad(1)

    if not register_device():
        log.warning("Falha ao registrar. Continuando mesmo assim...")

    # ── Boost de captura + ganho de software ──────────────────────────────
    # A PS3 Eye fica em cima da TV; com a TV alta o SNR cai. Aumentamos o
    # ganho do PulseAudio/ALSA e o multiplicador de software para que o
    # OpenWakeWord consiga detectar "alexa" mesmo com o usuário no sofá.
    apply_capture_level("150")
    log.info("🔊 [ÁUDIO] ALSA Capture ajustado para 150%%")
    log.info(
        "🔊 [ÁUDIO] Ganho de software: %.1fx | Threshold OWW: %.2f",
        CFG.software_gain, CFG.oww_threshold,
    )

    threading.Thread(target=websocket_loop, daemon=True).start()
    threading.Thread(target=stream_worker, daemon=True).start()
    threading.Thread(target=_audio_processing_worker, daemon=True).start()

    log.info("🎧 [Satélite da Sala] Ouvindo...")
    log.info("👉 Diga '%s' para me chamar!", STATE.wake_word.upper())

    device_index, device_channels, device_samplerate = find_input_device(CFG.preferred_mic_name)
    log.info(
        "🎙️ [ÁUDIO] Input selecionado: index=%s, channels=%s, samplerate=%s, preferido='%s'",
        device_index, device_channels, device_samplerate, CFG.preferred_mic_name,
    )

    try:
        with open_input_stream(device_index, device_channels, device_samplerate, audio_callback):
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        log.info("Encerrando satélite...")
    except Exception as e:
        # Loga o traceback completo — é exatamente isso que estava faltando
        # nos logs do systemd para diagnosticar o crash-loop do serviço.
        log.critical("Erro fatal no stream de áudio: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    log.info("--- SATELLITE LOCAL (ALFREDO) ---")
    main()