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
        
    async def power_on(self):
        """Tenta ligar a TV via SmartThings (Nível 1) ou Wake-on-LAN (Nível 2).
        
        Retorna True se um comando ABSOLUTO de ligar foi disparado (SmartThings
        confirmado ou magic packet WOL enviado). O chamador usa esse retorno
        para decidir se ainda precisa (ou não) recorrer ao botão de controle
        remoto local, que é um TOGGLE e pode desligar a TV de volta.
        """
        if self.smartthings_pat and self.smartthings_device_id:
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

    async def power_off(self):
        """Desliga a TV via SmartThings (Nível 1) ou controle remoto (Nível 2)."""
        if self.smartthings_pat and self.smartthings_device_id:
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

    async def _run_local_command(self, func, *args, **kwargs):
        """Executa um comando local tratando exceções de conexão."""
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except ConnectionFailure:
            logger.warning(f"Falha de conexão com a TV no IP {self.ip}. TV pode estar desligada ou rede inacessível.")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao conectar com a TV: {e}")
            return None

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
        if self.smartthings_pat and self.smartthings_device_id:
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

        logger.warning(
            f"Fallback para KEY_MUTE local (TOGGLE, não absoluto) ao tentar mute={mute}. "
            "Configure o SmartThings PAT/Device ID para um controle de mudo confiável."
        )
        return await self._run_local_command(self.tv.send_key, "KEY_MUTE")

    async def set_volume(self, volume: int):
        """Ajusta o volume da TV."""
        if self.smartthings_pat and self.smartthings_device_id:
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
        """Abre um aplicativo na TV pelo ID — prioriza rede local (mais confiável)."""
        logger.info(f"Abrindo app {app_id} na TV {self.ip}")
        # Rede local primeiro: o WebSocket directo run_app() é mais confiável
        # que o SmartThings custom.launchapp (que frequentemente retorna 200
        # sem realmente abrir o app em TVs Samsung).
        result = await self._run_local_command(self.tv.run_app, app_id)
        if result:
            logger.info(f"App {app_id} aberto via rede local.")
            return True
        # Fallback: SmartThings
        if self.smartthings_pat and self.smartthings_device_id:
            try:
                url = f"https://api.smartthings.com/v1/devices/{self.smartthings_device_id}/commands"
                headers = {"Authorization": f"Bearer {self.smartthings_pat}"}
                payload = {"commands": [{"component": "main", "capability": "custom.launchapp", "command": "launchApp", "arguments": [app_id]}]}
                response = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=5)
                if response.status_code == 200:
                    logger.info("App aberto via SmartThings com sucesso.")
                    return True
                logger.warning(f"SmartThings falhou ao abrir app. Code: {response.status_code}")
            except Exception as e:
                logger.error(f"Erro ao abrir app via SmartThings: {e}")
        return False

    async def get_status(self):
        """Verifica o status atual da TV e informações de rede."""
        info = await self._run_local_command(self.tv.rest_device_info)
        return info if info else {"status": "offline"}

    async def get_app_list(self):
        """Obtém a lista de aplicativos instalados na TV (com seus IDs)."""
        return await self._run_local_command(self.tv.app_list)
