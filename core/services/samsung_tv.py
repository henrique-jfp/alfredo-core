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
        """Ajusta o volume da TV."""
        if await self._ensure_smartthings():
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                payload = {"commands": [{"component": "main", "capability": "audioVolume", "command": "setVolume", "arguments": [volume]}]}
                await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                return True
            except Exception as e:
                logger.error(f"Erro ao setar volume via SmartThings: {e}")
        return False

    async def send_key(self, key: str):
        """Envia um botão do controle remoto."""
        logger.info(f"Enviando tecla {key} para a TV {self.ip}")
        return await self._run_local_command(self.tv.send_key, key)
        
    async def open_app(self, app_id: str):
        """Abre um aplicativo na TV pelo ID — tenta múltiplas estratégias.

        NOTA: O comando DEEP_LINK via samsungtvws (local) frequentemente
        retorna sucesso (None) mesmo quando a TV ignora o app — é um falso
        positivo do protocolo WebSocket em TVs Tizen 6.0+. Por isso a
        PRIORIDADE é SmartThings quando disponível.
        """
        logger.info(f"Abrindo app {app_id} na TV {self.ip}")

        # ── Estratégia 1: SmartThings (nuvem) ──────────────────────────────
        # Prioridade máxima: a TV tem custom.launchapp (confirmado em
        # diagnose_smartthings); a nuvem SmartThings é o único método
        # confiável em TVs Tizen 6.0+ (2021+).
        if await self._ensure_smartthings():
            url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
            headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
            for capability_name in (
                "custom.launchapp",
                "x.com.samsung.da.launchapp",
                "samsungvd.launchService",
            ):
                # Variações de argumento: diferentes TVs aceitam formatos diferentes
                for args in (
                    [{"appId": app_id, "metaData": {}}],
                    [{"appId": app_id, "metaData": {"app_type": "DEEP_LINK"}}],
                    [app_id],
                ):
                    try:
                        payload = {
                            "commands": [
                                {
                                    "component": "main",
                                    "capability": capability_name,
                                    "command": "launchApp",
                                    "arguments": args,
                                }
                            ]
                        }
                        response = await asyncio.to_thread(
                            requests.post, url, headers=headers, json=payload, timeout=5
                        )
                        if response.status_code == 200:
                            logger.info(
                                "App %s aberto via SmartThings (%s, args=%s).",
                                app_id, capability_name, args,
                            )
                            return True
                        logger.warning(
                            "SmartThings %s args=%s falhou. HTTP %s: %s",
                            capability_name, args,
                            response.status_code,
                            response.text[:200],
                        )
                    except Exception as e:
                        logger.error(
                            "Erro no SmartThings (%s, args=%s): %s",
                            capability_name, args, e,
                        )

        # ── Estratégia 2: run_app local (fallback se SmartThings falhou) ──
        # Historicamente o DEEP_LINK retorna sucesso falso em TVs recentes,
        # mas em modelos mais antigos (Tizen 5.x) ainda funciona de verdade.
        for app_type in ("DEEP_LINK", "NATIVE_LAUNCH"):
            result = await self._run_local_command(self.tv.run_app, app_id, app_type)
            if result is not self._LOCAL_FAIL:
                logger.info("App %s: comando %s enviado (sem garantia de execução).", app_id, app_type)
                return True

        logger.error(f"Todas as estratégias falharam para abrir app {app_id}.")
        return False

    async def get_status(self):
        """Verifica o status atual da TV e informações de rede."""
        info = await self._run_local_command(self.tv.rest_device_info)
        return info if info is not self._LOCAL_FAIL else {"status": "offline"}

    async def get_app_list(self):
        """Obtém a lista de aplicativos instalados na TV (com seus IDs)."""
        return await self._run_local_command(self.tv.app_list)
