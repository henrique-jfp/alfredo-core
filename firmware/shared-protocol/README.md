# Shared Protocol - Alfredo Home OS

Todo firmware de satélite, independente de marca, chip ou modelo, deve implementar esta interface de comunicação. O servidor reage às `capabilities` declaradas no boot.

## 1. Registro de Dispositivo (Boot)
Ao se conectar ao Wi-Fi, o dispositivo deve realizar um `POST` no endpoint `/api/devices/register` com seu estado e capacidades de hardware.

**Endpoint:** `POST /api/devices/register`
**Headers:**
- `Authorization: Bearer <SATELLITE_AUTH_TOKEN>`
- `Content-Type: application/json`

**Body Payload:**
```json
{
  "device_id": "sala-001",
  "room_id": "ROOM_LIVING",
  "hardware": "esp32s3-deepseek-ball",
  "firmware_version": "1.0.0",
  "capabilities": ["display_round_240", "touch", "microphone", "speaker", "battery", "sd_card"]
}
```
**Resposta (200 OK):**
```json
{
  "status": "registered",
  "message": "Welcome to Alfredo Home OS"
}
```

## 2. Envio de Áudio
*(A ser detalhado na Etapa 1)*
**Endpoint:** `POST /api/voice`

## 3. WebSocket de Eventos
*(A ser detalhado na Etapa 2/3)*
**Endpoint:** `WS /ws/satellite/{device_id}`
