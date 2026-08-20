import json
import logging
import base64
import time
import tinytuya
from tinytuya.Contrib import IRRemoteControlDevice, RFRemoteControlDevice

logger = logging.getLogger("alfredo.tuya_hub")

class TuyaHubManager:
    """Manager to communicate directly with Tuya IR/RF Hubs via local network."""
    
    def __init__(self):
        pass

    def _get_ir_device(self, dev_id: str, ip: str, local_key: str, version: str = "3.3") -> IRRemoteControlDevice.IRRemoteControlDevice:
        return IRRemoteControlDevice.IRRemoteControlDevice(
            dev_id=dev_id,
            address=ip,
            local_key=local_key,
            version=float(version),
            persist=True
        )

    def _get_rf_device(self, dev_id: str, ip: str, local_key: str, version: str = "3.3") -> RFRemoteControlDevice.RFRemoteControlDevice:
        return RFRemoteControlDevice.RFRemoteControlDevice(
            dev_id=dev_id,
            address=ip,
            local_key=local_key,
            version=float(version),
            persist=True
        )

    def send_ir(self, dev_id: str, ip: str, local_key: str, payload_base64: str, version: str = "3.3") -> bool:
        """Sends a learned IR payload base64 string to the hub."""
        try:
            device = self._get_ir_device(dev_id, ip, local_key, version)
            logger.info(f"Sending IR command to {dev_id} at {ip}")
            device.send_button(payload_base64)
            return True
        except Exception as e:
            logger.error(f"Failed to send IR command: {e}")
            return False

    def learn_ir(self, dev_id: str, ip: str, local_key: str, version: str = "3.3", timeout: int = 15) -> str | None:
        """Enters IR learning mode and returns the learned base64 payload."""
        try:
            device = self._get_ir_device(dev_id, ip, local_key, version)
            logger.info(f"Entering IR learning mode on {dev_id} at {ip}")
            learned = device.receive_button(timeout=timeout)
            return learned
        except Exception as e:
            logger.error(f"Failed to learn IR command: {e}")
            return None

    def send_rf(self, dev_id: str, ip: str, local_key: str, payload_base64: str, version: str = "3.3") -> bool:
        """Sends a learned RF payload base64 string to the hub."""
        try:
            device = self._get_rf_device(dev_id, ip, local_key, version)
            logger.info(f"Sending RF command to {dev_id} at {ip}")
            device.rf_send_button(payload_base64)
            return True
        except Exception as e:
            logger.error(f"Failed to send RF command: {e}")
            return False

    def learn_rf(self, dev_id: str, ip: str, local_key: str, freq: int = 433, version: str = "3.3", timeout: int = 15) -> str | None:
        """Enters RF learning mode and returns the learned base64 payload."""
        try:
            device = self._get_rf_device(dev_id, ip, local_key, version)
            logger.info(f"Entering RF learning mode on {dev_id} at {ip} for {freq}MHz")
            learned = device.rf_receive_button(freq=freq, timeout=timeout)
            return learned
        except Exception as e:
            logger.error(f"Failed to learn RF command: {e}")
            return None

tuya_hub_manager = TuyaHubManager()
