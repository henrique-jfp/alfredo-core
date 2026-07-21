import json
from typing import Union, Dict

def encode_json(data: Dict) -> str:
    try:
        return json.dumps(data)
    except Exception:
        return "{}"

def decode_json(text: str) -> Dict:
    try:
        return json.loads(text)
    except Exception:
        return {}

def build_identify_payload(device_id: str, room_id: str) -> str:
    return encode_json({
        "type": "IDENTIFY",
        "device_id": device_id,
        "room_id": room_id
    })
