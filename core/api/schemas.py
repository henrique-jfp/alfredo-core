from pydantic import BaseModel
from typing import List

class DeviceRegisterRequest(BaseModel):
    device_id: str
    room_id: str
    hardware: str
    firmware_version: str
    capabilities: List[str]

class DeviceRegisterResponse(BaseModel):
    status: str
    message: str
