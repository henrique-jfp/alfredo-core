import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from wakeonlan import send_magic_packet
import requests
from samsungtvws import SamsungTVWS
from samsungtvws.exceptions import ConnectionFailure

logger = logging.getLogger("alfredo.samsung_tv")

# Mapeamento de apps para teclas de atalho do controle Samsung.
# Estas são as teclas dedicadas presentes nos controles remotos
# originais — muito mais confiáveis que launchApp via API para
# TVs Tizen 6.0+ (Crystal UHD, Series 7+).
_APP_SHORTCUTS = {
    "netflix": "KEY_NETFLIX",
    "net flix": "KEY_NETFLIX",
    "youtube": "KEY_YOUTUBE",
    "you tube": "KEY_YOUTUBE",
    "prime video": "KEY_PRIME_VIRTUAL",
    "prime": "KEY_PRIME_VIRTUAL",
    "amazon prime": "KEY_PRIME_VIRTUAL",
    "amazon": "KEY_PRIME_VIRTUAL",
    "spotify": "KEY_SPOTIFY",
    "disney": "KEY_DISNEY_PLUS",
    "disney plus": "KEY_DISNEY_PLUS",
    "disney+": "KEY_DISNEY_PLUS",
}

class SamsungTVManager:
    def __init__(self, ip: str, mac: str = None, smartthings_pat: str = None, smartthings_device_id: str = None):
        self.ip = ip
        self.mac = mac
        self.smartthings_pat = smartthings_pat
        self.smartthings_device_id = smartthings_device_id
        
        # Token storage for samsungtvws (saved locally to avoid prompting TV on every connection)
        self.token_file = os.path.join(os.getcwd(), "tmp", f"samsung_tv_token_{ip.replace('.', '_')}.txt")
        # Ensure tmp dir exists
        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        # Timeout de 15s para dar tempo de o usuário apertar "Permitir" na TV no primeiro acesso
        self.tv = SamsungTVWS(host=ip, port=8002, token_file=self.token_file, timeout=15)
        self._smartthings_checked = False
        self._smartthings_ok = False
        self._smartthings_reason = None
        
    async def power_on(self):
        """Tenta ligar a TV via SmartThings (Nível 1) ou Wake-on-LAN (Nível 2).
        
        Retorna True se um comando ABSOLUTO de ligar foi disparado (SmartThings
        confirmado ou magic packet WOL enviado). O chamador usa esse retorno
        para decidir se ainda precisa (ou não) recorrer ao botão de controle
        remoto local, que é um TOGGLE e pode desligar a TV de volta.
        """
        if await self._ensure_smartthings():
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                payload = {"commands": [{"component": "main", "capability": "switch", "command": "on"}]}
                response = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info("Sinal Power On enviado via SmartThings.")
                    return True
            except Exception as e:
                logger.error(f"Erro no Power On via SmartThings: {e}")

        if self.mac:
            send_magic_packet(self.mac)
            logger.info("Magic packet (WOL) enviado para ligar a TV.")
            return True

        return False

    async def diagnose_smartthings(self) -> Dict[str, Any]:
        """Valida se o PAT e o device_id funcionam antes de tentar comandos.

        Retorna um diagnóstico estruturado para diferenciar:
        - PAT inválido/expirado
        - device_id inexistente/inacessível
        - device acessível, mas sem as capabilities esperadas
        """
        if not self.smartthings_pat or not self.smartthings_device_id:
            return {
                "configured": False,
                "ok": False,
                "reason": "missing_credentials",
                "message": "SmartThings PAT ou device_id não configurado."
            }

        url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}"
        headers = {"Authorization": f"Bearer {self.smartthings_pat}"}

        try:
            response = await asyncio.to_thread(requests.get, url, headers=headers, timeout=5)
        except Exception as e:
            return {
                "configured": True,
                "ok": False,
                "reason": "request_error",
                "message": f"Falha ao consultar SmartThings: {e}"
            }

        if response.status_code == 401:
            return {
                "configured": True,
                "ok": False,
                "reason": "unauthorized",
                "message": "PAT do SmartThings inválido, expirado ou sem permissão para esta conta."
            }

        if response.status_code == 404:
            return {
                "configured": True,
                "ok": False,
                "reason": "device_not_found",
                "message": "Device ID não encontrado ou sem acesso a esse dispositivo no SmartThings."
            }

        if response.status_code != 200:
            return {
                "configured": True,
                "ok": False,
                "reason": "unexpected_status",
                "status_code": response.status_code,
                "message": f"SmartThings respondeu HTTP {response.status_code} ao consultar o device."
            }

        data = {}
        try:
            data = response.json() or {}
        except Exception:
            data = {}

        """Liga a TV via rede local usando WakeOnLan (WOL)."""
        if not self.mac:
            logger.error(f"MAC address não configurado para a TV {self.ip}. Necessário para WakeOnLan.")
            return False

        logger.info(f"Enviando WakeOnLan para a TV {self.ip} (MAC: {self.mac})")
        # WOL local funciona melhor via thread para evitar block se houver falhas subjacentes na biblioteca
        return await asyncio.to_thread(send_magic_packet, self.mac)

    async def power_off(self):
        """Desliga a TV enviando KEY_POWER via rede local."""
        logger.info("Enviando KEY_POWER para desligar a TV via rede local.")
        return await self._run_local_command(self.tv.send_key, "KEY_POWER")

    # Sentinel: retornado por _run_local_command quando a conexão falha
    _LOCAL_FAIL = object()

    async def _run_local_command(self, func, *args, **kwargs):
        """Executa um comando local tratando exceções de conexão.
        Retorna o resultado de func() ou _LOCAL_FAIL em caso de falha."""
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except ConnectionFailure:
            logger.warning(f"Falha de conexão com a TV no IP {self.ip}. TV pode estar desligada ou rede inacessível.")
            return self._LOCAL_FAIL
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar com a TV: {e}")
            return self._LOCAL_FAIL

    async def set_mute(self, mute: bool):
        """DESATIVADO.
        Em modo 100% LAN, não podemos determinar o estado absoluto do Mute na TV
        usando comandos básicos. O uso cego de KEY_MUTE funciona como toggle
        e causa problemas graves de sincronia (Ducking inverte o som).
        Portanto, definimos esta função como um "pass" seguro.
        O usuário deve utilizar a tecla MUTE offline ou via KEY_MUTE se quiser alternar manualmente.
        """
        logger.warning("Comando Mute ignorado: Sem SmartThings, é impossível garantir o estado absoluto. Evitando toggle acidental.")
        return False

    async def set_volume(self, volume: int):
        """DESATIVADO.
        Em modo 100% LAN, o volume absoluto também não é trivial em Tizen mais antigos sem UPNP ativo.
        """
        logger.warning(f"Volume absoluto {volume} ignorado: Suporte a LAN desativado para volume absoluto.")
        return False

    async def send_key(self, key: str, times: int = 1, key_press_delay: float | None = None):
        """Envia um botão do controle remoto, opcionalmente múltiplas vezes.

        Args:
            key: Código da tecla (ex: KEY_VOLDOWN, KEY_MUTE).
            times: Número de repetições da tecla.
            key_press_delay: Atraso entre cada pressão (None = usa o default
                             da biblioteca samsungtvws, que é 1s).
        """
        logger.info(f"Enviando tecla {key} para a TV {self.ip} (vezes={times})")
        return await self._run_local_command(self.tv.send_key, key, times=times, key_press_delay=key_press_delay)
        
    async def open_app(self, app_id: str, app_name: str = ""):
        """Abre um aplicativo na TV via LAN.
        
        Estratégias:
          1. Tecla de atalho Samsung (KEY_NETFLIX, KEY_YOUTUBE)
          2. run_app DEEP_LINK via WebSocket local
          3. run_app NATIVE_LAUNCH via WebSocket local
        """
        name = app_name.lower() if app_name else ""
        logger.info("Abrindo app id=%s name=%s na TV %s (Modo 100%% LAN)", app_id, name or "?", self.ip)

        # ── Estratégia 1: Tecla de atalho Samsung ──────────────────────────
        shortcut_key = _APP_SHORTCUTS.get(name) if name else None
        if shortcut_key:
            result = await self._run_local_command(self.tv.send_key, shortcut_key)
            if result is not self._LOCAL_FAIL:
                logger.info("App %s: tecla de atalho %s enviada.", app_id, shortcut_key)
                return True

        # ── Estratégia 2: DEEP_LINK ────────────────────────────────────────
        result = await self._run_local_command(self.tv.run_app, app_id, "DEEP_LINK")
        if result is not self._LOCAL_FAIL:
            logger.info("App %s: DEEP_LINK enviado.", app_id)
            return True

        # ── Estratégia 3: NATIVE_LAUNCH ────────────────────────────────────
        result = await self._run_local_command(self.tv.run_app, app_id, "NATIVE_LAUNCH")
        if result is not self._LOCAL_FAIL:
            logger.info("App %s: NATIVE_LAUNCH enviado.", app_id)
            return True

        logger.error("Todas as estratégias locais falharam para abrir app %s.", app_id)
        return False

    async def get_status(self):
        """Verifica o status atual da TV e informações de rede."""
        info = await self._run_local_command(self.tv.rest_device_info)
        return info if info is not self._LOCAL_FAIL else {"status": "offline"}

    async def get_app_list(self):
        """Obtém a lista de aplicativos instalados na TV (com seus IDs)."""
        return await self._run_local_command(self.tv.app_list)
