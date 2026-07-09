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
        """Tenta ligar a TV via SmartThings (Nível 1) ou Wake-on-LAN (Nível 2)."""
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
                
        # Fallback to Wake on LAN if MAC is available
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
                
        # Fallback to local network key
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
        """Ativa ou desativa o mudo da TV."""
        logger.info(f"Enviando mute={mute} para a TV {self.ip}")
        # KEY_MUTE funciona como toggle (mute/unmute) — o mesmo botão do controle remoto.
        # A lib samsungtvws não possui método unmute() separado.
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
        """Abre um aplicativo na TV pelo ID (ex: Netflix = 11101200001, YouTube = 111299001912)."""
        logger.info(f"Abrindo app {app_id} na TV {self.ip}")
        return await self._run_local_command(self.tv.run_app, app_id)

    async def get_status(self):
        """Verifica o status atual da TV e informações de rede."""
        info = await self._run_local_command(self.tv.rest_device_info)
        return info if info else {"status": "offline"}

    async def get_app_list(self):
        """Obtém a lista de aplicativos instalados na TV (com seus IDs)."""
        return await self._run_local_command(self.tv.app_list)
