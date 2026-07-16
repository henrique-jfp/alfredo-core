"""
Skill para controlar dispositivos de casa inteligente (lâmpadas, ventiladores,
tomadas) via Home Assistant. Segue o mesmo padrão de tv_skill.py:

  - execute_tool(self, arguments, context)
  - Resolução de cômodo em 3 etapas (target_room → room_id → fallback)
  - Retorna dict com direct_response para evitar segunda chamada ao Gemini
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("alfredo.smart_home_skill")


def _resolve_room_id(db, target_room: str | None, fallback_room_id: str | None) -> str | None:
    """Resolve um cômodo em 3 etapas, igual à tv_skill.py:

    1. Se target_room foi informado, tenta casar pelo nome na tabela rooms.
    2. Se não achou, usa o room_id do satélite (de onde a pessoa falou).
    3. Fallback: pega o primeiro cômodo cadastrado no banco.
    """
    from core.brain.memory import models

    room_row = None

    # Etapa 1 — nome do cômodo informado pelo usuário
    if target_room:
        t = target_room.lower().strip()

        # Tenta match exato por nome
        room_row = (
            db.query(models.Room)
            .filter(models.Room.name.ilike(t))
            .first()
        )
        if not room_row:
            # Tenta por room_id (ex: "ROOM_LIVING", "ROOM_OFFICE")
            room_row = (
                db.query(models.Room)
                .filter(models.Room.room_id.ilike(f"%{t}%"))
                .first()
            )
        if not room_row:
            # Tenta substring no nome (ex: "sala" → "Sala", "escritório" → "Escritório")
            room_row = (
                db.query(models.Room)
                .filter(models.Room.name.ilike(f"%{t}%"))
                .first()
            )

    # Etapa 2 — cômodo físico de onde o usuário falou
    if not room_row and fallback_room_id:
        room_row = (
            db.query(models.Room)
            .filter(models.Room.room_id == fallback_room_id)
            .first()
        )

    # Etapa 3 — primeiro cômodo disponível
    if not room_row:
        room_row = db.query(models.Room).first()

    return room_row.room_id if room_row else None


def _resolve_devices(
    db,
    room_id: str,
    device_type: str | None = None,
    device_name: str | None = None,
):
    """Retorna lista de SmartDevice do cômodo, opcionalmente filtrados."""
    from core.brain.memory import models

    q = db.query(models.SmartDevice).filter(
        models.SmartDevice.room_id == room_id,
        models.SmartDevice.is_active == True,
    )

    if device_type:
        q = q.filter(models.SmartDevice.device_type == device_type)
    if device_name:
        q = q.filter(models.SmartDevice.friendly_name.ilike(f"%{device_name}%"))

    return q.all()


class SmartHomeSkill:
    """Controla dispositivos de casa inteligente via Home Assistant."""

    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str | dict:
        action = arguments.get("action")
        device_type = arguments.get("device_type")
        device_name = arguments.get("device_name")
        target_room = arguments.get("target_room")

        db = context.get("db")
        fallback_room_id = context.get("room_id")

        if not db:
            return "Erro: banco de dados não disponível."

        if not action:
            return {"direct_response": "Não entendi qual ação você quer executar. Pode repetir?"}

        # ── Resolve o cômodo ──────────────────────────────────────────
        resolved_room_id = _resolve_room_id(db, target_room, fallback_room_id)
        if not resolved_room_id:
            return {
                "direct_response": (
                    "Não encontrei nenhum cômodo cadastrado. "
                    "Peça ao dono da casa para cadastrar os cômodos no painel de controle."
                )
            }

        # ── Busca o(s) dispositivo(s) ─────────────────────────────────
        devices = _resolve_devices(db, resolved_room_id, device_type, device_name)
        if not devices:
            if device_name:
                msg = f"Não encontrei nenhum dispositivo com o nome '{device_name}'"
            elif device_type:
                tipo_pt = _translate_device_type(device_type)
                msg = f"Não encontrei nenhum(a) {tipo_pt} cadastrado(a) nesse cômodo"
            else:
                msg = "Não encontrei nenhum dispositivo cadastrado nesse cômodo"
            return {"direct_response": f"{msg}. Primeiro cadastre os dispositivos no painel de controle."}

        # ── Executa a ação no Home Assistant ──────────────────────────
        from core.services.home_assistant import HomeAssistantManager

        ha = HomeAssistantManager()
        action_pt = _translate_action(action)
        results = []

        for dev in devices:
            try:
                if action == "turn_on":
                    ha.turn_on(dev.entity_id)
                elif action == "turn_off":
                    ha.turn_off(dev.entity_id)
                elif action == "toggle":
                    ha.toggle(dev.entity_id)
                elif action == "set_brightness":
                    b = arguments.get("brightness", arguments.get("value", 128))
                    ha.set_brightness(dev.entity_id, int(b))
                elif action == "set_speed":
                    speed = arguments.get("speed", arguments.get("value", "medium"))
                    ha.set_speed(dev.entity_id, speed)
                else:
                    return {"direct_response": f"Ação '{action}' não é suportada para dispositivos inteligentes."}

                results.append(dev.friendly_name)
            except Exception as e:
                logger.error(f"Erro ao controlar {dev.entity_id}: {e}")
                results.append(f"{dev.friendly_name} (falha)")

        if not results:
            return {"direct_response": "Nenhum dispositivo foi controlado."}

        # ── Resposta direta ──────────────────────────────────────────
        if len(results) == 1:
            return {"direct_response": f"{action_pt} {results[0]}."}
        return {"direct_response": f"{action_pt} {', '.join(results[:-1])} e {results[-1]}."}


# ── helpers de tradução ────────────────────────────────────────────────

def _translate_action(action: str) -> str:
    mapping = {
        "turn_on": "Liguei",
        "turn_off": "Desliguei",
        "toggle": "Alternei",
        "set_brightness": "Ajustei o brilho de",
        "set_speed": "Ajustei a velocidade de",
    }
    return mapping.get(action, action)


def _translate_device_type(dt: str) -> str:
    mapping = {
        "light": "luz",
        "fan": "ventilador",
        "switch": "tomada",
        "lock": "fechadura",
        "sensor": "sensor",
    }
    return mapping.get(dt, dt)
