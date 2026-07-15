"""
key_manager.py

Gerenciamento centralizado de chaves de API (Gemini, Groq).
- Round-robin thread-safe para múltiplas chaves
- Cooldown automático em caso de rate limit (429)
- Health-check de chaves em cooldown
- Suporte a GEMINI_API_KEYS (plural, separado por vírgula) e GEMINI_API_KEY (singular)
- Suporte a GROQ_API_KEYS (plural) e GROQ_API_KEY (singular)
"""

import os
import re
import time
import threading
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("alfredo.key_manager")

# ──────────────────────────────────────────────────────────────
# Pool persistente de conexão Gemini
# Evita destruir o pool gRPC em toda requisição.
# _configure_genai() só reconfigura o SDK quando a chave muda.
# ──────────────────────────────────────────────────────────────
_last_configured_gemini_key: str | None = None

def configure_genai(api_key: str) -> None:
    """Configura o SDK Gemini apenas se a chave mudou desde a última chamada.
    
    A primeira chamada sempre configura. Chamadas subsequentes com a
    mesma chave são NO-OP — o pool gRPC permanece intacto, economizando
    500ms–2s de overhead de conexão por requisição.
    """
    global _last_configured_gemini_key
    if api_key != _last_configured_gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _last_configured_gemini_key = api_key
        logger.debug(f"Gemini SDK reconfigurado para nova chave API")
    else:
        logger.debug(f"Gemini SDK já configurado com esta chave — pool preservado")


def reset_genai_pool():
    """Força reconfiguração na próxima chamada (uso interno para testes)."""
    global _last_configured_gemini_key
    _last_configured_gemini_key = None

# --------------------------------------------------------------------------- #
# Estado global
# --------------------------------------------------------------------------- #

_gemini_keys: List[str] = []
_groq_keys: List[str] = []
_gemini_idx = 0
_groq_idx = 0
_gemini_cooldown: dict = {}   # key -> timestamp until which it's blocked
_groq_cooldown: dict = {}     # key -> timestamp until which it's blocked
_gemini_total_requests = 0
_groq_total_requests = 0
_lock = threading.Lock()
COOLDOWN_SECONDS = 60  # Tempo padrão de cooldown após 429

# --------------------------------------------------------------------------- #
# Carga de chaves
# --------------------------------------------------------------------------- #

def _load_env_keys(env_plural: str, env_singular: str) -> List[str]:
    """Carrega chaves de uma variável de ambiente no formato plural ou singular."""
    keys_env = os.getenv(env_plural, "")
    if keys_env:
        raw_keys = re.split(r"[\n,;]+", keys_env)
        keys = [key.strip().strip('"').strip("'") for key in raw_keys if key.strip()]
    else:
        single = os.getenv(env_singular, "").strip()
        keys = [single.strip('"').strip("'")] if single else []

    # Deduplica
    seen = set()
    deduped = []
    for key in keys:
        if key and key not in seen:
            deduped.append(key)
            seen.add(key)
    return deduped


def reload_keys():
    """Recarrega todas as chaves do ambiente. Chamado na inicialização."""
    global _gemini_keys, _groq_keys, _gemini_cooldown, _groq_cooldown
    with _lock:
        _gemini_keys = _load_env_keys("GEMINI_API_KEYS", "GEMINI_API_KEY")
        _groq_keys = _load_env_keys("GROQ_API_KEYS", "GROQ_API_KEY")

        # Limpa cooldowns de chaves que não existem mais
        _gemini_cooldown = {k: v for k, v in _gemini_cooldown.items() if k in _gemini_keys}
        _groq_cooldown = {k: v for k, v in _groq_cooldown.items() if k in _groq_keys}

    if _gemini_keys:
        logger.info(f"{len(_gemini_keys)} chave(s) Gemini carregada(s)")
    if _groq_keys:
        logger.info(f"{len(_groq_keys)} chave(s) Groq carregada(s)")


# Garante que as chaves sejam carregadas na importação
reload_keys()

# --------------------------------------------------------------------------- #
# Seleção round-robin
# --------------------------------------------------------------------------- #

def _next_key(
    keys: List[str],
    idx: int,
    cooldown: dict,
    total_requests: int
) -> Tuple[Optional[str], int, int, int]:
    """
    Retorna a próxima chave disponível (sem cooldown).
    Retorna (chave, índice_1based, total_keys, posição_no_array).
    Se todas em cooldown, retorna a primeira mesmo em cooldown.
    """
    if not keys:
        return None, 0, 0, 0

    n = len(keys)
    all_in_cooldown = all(
        cooldown.get(k, 0) > time.time() for k in keys
    )

    for attempt in range(n):
        pos = (idx + attempt) % n
        key = keys[pos]
        if all_in_cooldown or cooldown.get(key, 0) <= time.time():
            return key, pos + 1, n, pos

    # Fallback: todas em cooldown, usa a primeira
    return keys[0], 1, n, 0


def next_gemini_key() -> Tuple[Optional[str], int, int]:
    """
    Retorna (chave, número_1based, total).
    Thread-safe.
    """
    global _gemini_idx, _gemini_total_requests
    with _lock:
        key, num, total, pos = _next_key(
            _gemini_keys, _gemini_idx, _gemini_cooldown, _gemini_total_requests
        )
        if key:
            _gemini_idx = (pos + 1) % total if total > 0 else 0
            _gemini_total_requests += 1
        return key, num, total


def next_groq_key() -> Tuple[Optional[str], int, int]:
    """
    Retorna (chave, número_1based, total).
    Thread-safe.
    """
    global _groq_idx, _groq_total_requests
    with _lock:
        key, num, total, pos = _next_key(
            _groq_keys, _groq_idx, _groq_cooldown, _groq_total_requests
        )
        if key:
            _groq_idx = (pos + 1) % total if total > 0 else 0
            _groq_total_requests += 1
        return key, num, total


# --------------------------------------------------------------------------- #
# Cooldown
# --------------------------------------------------------------------------- #

def mark_gemini_cooldown(key: str, seconds: int = COOLDOWN_SECONDS):
    """Marca uma chave Gemini para cooldown por N segundos."""
    with _lock:
        _gemini_cooldown[key] = time.time() + seconds
        logger.warning(f"Chave Gemini [{key[:12]}...] em cooldown por {seconds}s")


def mark_groq_cooldown(key: str, seconds: int = COOLDOWN_SECONDS):
    """Marca uma chave Groq para cooldown por N segundos."""
    with _lock:
        _groq_cooldown[key] = time.time() + seconds
        logger.warning(f"Chave Groq [{key[:12]}...] em cooldown por {seconds}s")


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #

def get_status() -> dict:
    """Retorna status completo de todas as chaves."""
    with _lock:
        now = time.time()
        gemini_keys_status = []
        for i, k in enumerate(_gemini_keys):
            cooldown_until = _gemini_cooldown.get(k, 0)
            gemini_keys_status.append({
                "index": i + 1,
                "key_preview": k[:12] + "...",
                "in_cooldown": cooldown_until > now,
                "cooldown_remaining_s": max(0, int(cooldown_until - now)) if cooldown_until > now else 0,
            })

        groq_keys_status = []
        for i, k in enumerate(_groq_keys):
            cooldown_until = _groq_cooldown.get(k, 0)
            groq_keys_status.append({
                "index": i + 1,
                "key_preview": k[:12] + "...",
                "in_cooldown": cooldown_until > now,
                "cooldown_remaining_s": max(0, int(cooldown_until - now)) if cooldown_until > now else 0,
            })

        return {
            "gemini": {
                "total_keys": len(_gemini_keys),
                "keys": gemini_keys_status,
                "total_requests": _gemini_total_requests,
            },
            "groq": {
                "total_keys": len(_groq_keys),
                "keys": groq_keys_status,
                "total_requests": _groq_total_requests,
            },
        }


def get_simple_status() -> dict:
    """Versão simplificada para o dashboard (sem detalhes de cada chave)."""
    with _lock:
        gemini_active = sum(
            1 for k in _gemini_keys if _gemini_cooldown.get(k, 0) <= time.time()
        )
        groq_active = sum(
            1 for k in _groq_keys if _groq_cooldown.get(k, 0) <= time.time()
        )
        return {
            "gemini_total_keys": len(_gemini_keys),
            "gemini_active_keys": gemini_active,
            "gemini_in_cooldown": len(_gemini_keys) - gemini_active,
            "gemini_total_requests": _gemini_total_requests,
            "groq_total_keys": len(_groq_keys),
            "groq_active_keys": groq_active,
            "groq_in_cooldown": len(_groq_keys) - groq_active,
            "groq_total_requests": _groq_total_requests,
        }
