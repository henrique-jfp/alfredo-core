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

        capabilities = []
        try:
            for component in data.get("components", []):
                for cap in component.get("capabilities", []):
                    cap_id = cap.get("id")
                    if cap_id:
                        capabilities.append(cap_id)
        except Exception:
            capabilities = []

        supports_switch = "switch" in capabilities
        supports_mute = "audioMute" in capabilities
        supports_volume = "audioVolume" in capabilities
        has_launchapp = any(
            "launchapp" in c.lower() or "launch" in c.lower()
            for c in capabilities
        )

        # Loga todas as capabilities disponíveis para diagnóstico de abertura de apps
        logger.info(
            "SmartThings capabilities disponíveis na TV: %s", capabilities
        )

        return {
            "configured": True,
            "ok": supports_switch and (supports_mute or supports_volume),
            "reason": "ok" if (supports_switch and (supports_mute or supports_volume)) else "missing_capabilities",
            "device": {
                "id": data.get("deviceId") or self.smartthings_device_id,
                "label": data.get("label"),
                "name": data.get("name"),
                "manufacturer": data.get("manufacturerName"),
            },
            "capabilities": {
                "switch": supports_switch,
                "audioMute": supports_mute,
                "audioVolume": supports_volume,
                "launchapp": has_launchapp,
                "all": capabilities,
            },
            "message": (
                "SmartThings OK."
                if supports_switch and (supports_mute or supports_volume)
                else "Device acessível, mas não expõe capabilities esperadas para controle confiável da TV."
            )
        }

    async def _ensure_smartthings(self) -> bool:
        """Faz uma checagem única e evita repetir requests que já falharam."""
        if self._smartthings_checked:
            return self._smartthings_ok

        diag = await self.diagnose_smartthings()
        self._smartthings_checked = True
        self._smartthings_ok = bool(diag.get("ok"))
        self._smartthings_reason = diag.get("reason")

        if not self._smartthings_ok:
            logger.warning(
                "SmartThings indisponível para a TV %s (%s): %s",
                self.ip,
                self._smartthings_reason,
                diag.get("message"),
            )

        return self._smartthings_ok

    async def power_off(self):
        """Desliga a TV via SmartThings (Nível 1) ou controle remoto (Nível 2)."""
        if await self._ensure_smartthings():
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                payload = {"commands": [{"component": "main", "capability": "switch", "command": "off"}]}
                response = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info("Sinal Power Off enviado via SmartThings.")
                    return True
            except Exception as e:
                logger.error(f"Erro no Power Off via SmartThings: {e}")

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
        """Define o estado de mudo da TV de forma ABSOLUTA (não alterna).

        BUG CORRIGIDO: a versão anterior sempre enviava KEY_MUTE, que é um
        botão de ALTERNÂNCIA no controle remoto Samsung — o parâmetro `mute`
        era, na prática, ignorado. Como o satélite dispara auto-mute/unmute
        em toda wake word (ver satellite_server/main.py), cada comando de voz
        gerava 2-3 toggles fora de sincronia, deixando o estado do som
        praticamente aleatório.

        Agora priorizamos o SmartThings (capability 'audioMute'), que aceita
        comandos absolutos 'mute' / 'unmute'. Só caímos no botão local
        (KEY_MUTE, toggle) se o SmartThings não estiver configurado ou falhar
        — nesse caso não há garantia de que o resultado final seja o pedido.
        """
        if await self._ensure_smartthings():
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                command = "mute" if mute else "unmute"
                payload = {"commands": [{"component": "main", "capability": "audioMute", "command": command}]}
                response = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Mute={mute} definido via SmartThings (comando absoluto, sem toggle).")
                    return True
                logger.warning(f"SmartThings respondeu {response.status_code} ao tentar mute={mute}.")
            except Exception as e:
                logger.error(f"Erro ao definir mute via SmartThings: {e}")

        logger.error(
            f"\n"
            f"{'='*60}\n"
            f"⚠️  FALLBACK CRÍTICO: SmartThings indisponível para comando mute={mute}\n"
            f"{'='*60}\n"
            f"Motivo: SmartThings PAT inválido/expirado ou device_id incorreto.\n"
            f"Usando KEY_MUTE local (TOGGLE) — o resultado pode ser o OPOSTO do pedido,\n"
            f"já que KEY_MUTE alterna o estado atual em vez de defini-lo absolutamente.\n"
            f"Para corrigir: verifique as credenciais do SmartThings no Dashboard.\n"
            f"{'='*60}"
        )
        return await self._run_local_command(self.tv.send_key, "KEY_MUTE")

    async def set_volume(self, volume: int):
        """Ajusta o volume da TV.

        Estratégia:
          Apenas SmartThings (comando absoluto 'setVolume').
          **Não há fallback local** — o satélite já trata "volume no X"
          offline via _handle_volume, que usa KEY_VOLDOWN/VOLUP sem
          bottom-out (evita conflito com o ducking do OWW).

        Se o SmartThings falhar, o servidor retorna False (a LLM pode
        informar que não foi possível ajustar o volume).
        """
        if await self._ensure_smartthings():
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                payload = {"commands": [{"component": "main", "capability": "audioVolume", "command": "setVolume", "arguments": [volume]}]}
                await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                logger.info(f"Volume setado para {volume} via SmartThings.")
                return True
            except Exception as e:
                logger.error(f"Erro ao setar volume via SmartThings: {e}")

        logger.warning(f"Volume {volume}: SmartThings falhou. "
                       "O satélite deve tratar este comando offline.")
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
        
    async def _st_command(self, capability: str, command: str, arguments: list) -> bool:
        """Envia um comando SmartThings e retorna True se HTTP 200."""
        if not await self._ensure_smartthings():
            return False
        url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
        headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
        payload = {
            "commands": [{
                "component": "main",
                "capability": capability,
                "command": command,
                "arguments": arguments,
            }]
        }
        try:
            r = await asyncio.to_thread(
                requests.post, url, headers=headers, json=payload, timeout=5
            )
            return r.status_code == 200
        except Exception:
            return False

    async def open_app(self, app_id: str, app_name: str = ""):
        """Abre um aplicativo na TV — tenta múltiplas estratégias em ordem.

        Cada estratégia retorna imediatamente se bem-sucedida, exceto custom.launchapp
        que pode dar falso positivo.

        Estratégias (em ordem de prioridade):
          1. Tecla de atalho Samsung (KEY_NETFLIX, KEY_YOUTUBE etc.)
          2. run_app DEEP_LINK via WebSocket local
          3. run_app NATIVE_LAUNCH via WebSocket local
          4. SmartThings custom.launchapp — fallback genérico (ID do app)
        """
        name = app_name.lower() if app_name else ""
        app_ids = [aid.strip() for aid in app_id.split(",") if aid.strip()]
        logger.info("Abrindo app ids=%s name=%s na TV %s", app_ids, name or "?", self.ip)

        # ── O ULTIMATE SHOTGUN APPROACH ────────────────────────────────────
        # As APIs da Samsung (SmartThings e WebSockets) costumam retornar sucesso (200 OK)
        # mesmo quando a TV ignora o comando. Portanto, disparar apenas um e retornar
        # causa falhas silenciosas. Vamos disparar TODOS os métodos conhecidos, para
        # todos os IDs (novos e velhos) do app. Como todos têm o mesmo objetivo (abrir o app),
        # a TV processará o que funcionar e ignorará o resto.
        any_success = False

        # 1. REST API (Porta 8001) - Mais confiável para apps com ID
        for aid in app_ids:
            result = await self._run_local_command(self.tv.rest_app_run, aid)
            if result is not self._LOCAL_FAIL:
                logger.info("App %s: REST API rest_app_run executado.", aid)
                any_success = True

        # 2. SmartThings custom.launchapp
        for aid in app_ids:
            for args in ([aid], [{"appId": aid, "metaData": {}}]):
                ok = await self._st_command("custom.launchapp", "launchApp", args)
                if ok:
                    logger.info("App %s: SmartThings custom.launchapp aceitou (args=%s).", aid, args)
                    any_success = True

        # 3. WebSocket run_app (Porta 8002) - DEEP_LINK e NATIVE_LAUNCH
        for aid in app_ids:
            r1 = await self._run_local_command(self.tv.run_app, aid, "DEEP_LINK")
            r2 = await self._run_local_command(self.tv.run_app, aid, "NATIVE_LAUNCH")
            if r1 is not self._LOCAL_FAIL or r2 is not self._LOCAL_FAIL:
                logger.info("App %s: WebSocket run_app enviado.", aid)
                any_success = True

        # 4. Tecla de Atalho (KEY_NETFLIX, etc.)
        shortcut_key = _APP_SHORTCUTS.get(name) if name else None
        if shortcut_key:
            result = await self._run_local_command(self.tv.send_key, shortcut_key)
            if result is not self._LOCAL_FAIL:
                logger.info("App %s: tecla de atalho %s enviada.", app_ids, shortcut_key)
                any_success = True

        if any_success:
            return True

        logger.error("Todas as estratégias falharam fatalmente para abrir app %s.", app_ids)
        return False

    async def get_status(self):
        """Verifica o status atual da TV e informações de rede."""
        info = await self._run_local_command(self.tv.rest_device_info)
        return info if info is not self._LOCAL_FAIL else {"status": "offline"}

    async def get_app_list(self):
        """Obtém a lista de aplicativos instalados na TV (com seus IDs)."""
        return await self._run_local_command(self.tv.app_list)
