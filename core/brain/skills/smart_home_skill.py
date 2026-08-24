"""
Skill para controlar dispositivos de casa inteligente (lâmpadas, ventiladores,
tomadas) via Home Assistant. Segue o mesmo padrão de tv_skill.py:

  - execute_tool(self, arguments, context)
  - Resolução de cômodo em 3 etapas (target_room → room_id → fallback)
  - Retorna dict com direct_response para evitar segunda chamada ao Gemini

v2 – Otimizações:
  - Prioriza cenas do HA (scene.*) sobre entidades individuais
  - Executa chamadas ao HA em background thread (não bloqueia o TTS)
  - Retry com backoff em caso de falha de rede
  - Resposta sempre "Ok." para latência mínima
  - Suporta múltiplos comandos (batch) na mesma requisição
"""
import logging
import threading
import time
from typing import Dict, Any, List

logger = logging.getLogger("alfredo.smart_home_skill")


# ═══════════════════════════════════════════════════════════════════════════
# RESOLUÇÃO DE CÔMODO
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_room_id(db, target_room: str | None, fallback_room_id: str | None) -> str | None:
    """Resolve um cômodo em 3 etapas, igual à tv_skill.py:

    1. Se target_room foi informado, tenta casar pelo nome na tabela rooms.
    2. Se não achou, usa o room_id do satélite (de onde a pessoa falou).
    3. Fallback: pega o primeiro cômodo cadastrado no banco.
    """
    from core.brain.memory import models

    room_row = None

    # Etapa 1 — target_room informado pelo parser
    if target_room:
        t = target_room.lower().strip()

        # Se já veio como ROOM_* (do parser data-driven), busca direto
        if t.startswith("room_"):
            room_row = (
                db.query(models.Room)
                .filter(models.Room.room_id == target_room)
                .first()
            )
        else:
            # Tenta match por nome (sem artigos/preposições)
            t_clean = t.replace(" do ", " ").replace(" da ", " ").replace(" de ", " ").replace(" no ", " ").replace(" na ", " ")
            t_clean = " ".join(t_clean.split())

            room_row = (
                db.query(models.Room)
                .filter(models.Room.name.ilike(t_clean))
                .first()
            )
            if not room_row:
                room_row = (
                    db.query(models.Room)
                    .filter(models.Room.room_id.ilike(f"%{t_clean}%"))
                    .first()
                )
            if not room_row:
                room_row = (
                    db.query(models.Room)
                    .filter(models.Room.name.ilike(f"%{t_clean}%"))
                    .first()
                )
            if not room_row:
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


# ═══════════════════════════════════════════════════════════════════════════
# RESOLUÇÃO DE DISPOSITIVOS
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_devices(db, room_id: str, device_type: str | None = None, device_name: str | None = None):
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


# ═══════════════════════════════════════════════════════════════════════════
# SELEÇÃO INTELIGENTE DE CENA vs ENTIDADE
# ═══════════════════════════════════════════════════════════════════════════

def _pick_best_device(devices: list, action: str, device_name: str | None, device_type: str | None) -> list:
    """Dado uma lista de dispositivos, seleciona o melhor subconjunto
    priorizando cenas do HA (scene.*) sobre entidades individuais.

    REGRAS IMPORTANTES (baseadas no hardware físico):
      - LUZ é um TOGGLE: scene.luz_* liga E desliga (mesmo botão RF)
        → Para turn_on E turn_off de luz, usa scene.luz_*
        → NUNCA usar scene.desligar_* para desligar só a luz!
      - VENTILADOR off: usa scene.desligar_ventilador_*
      - "DESLIGAR TUDO": usa scene.desligar_* (master off)
        → Só quando device_name="desligar" (pedido explícito)
    """
    if not devices:
        return []

    scenes = [d for d in devices if d.entity_id.startswith("scene.")]
    non_scenes = [d for d in devices if not d.entity_id.startswith("scene.")]

    # Se buscou por nome específico (ex: "ventilador 3", "desligar"), retorna direto
    if device_name:
        return devices

    if not scenes:
        return non_scenes

    # ── LUZ: sempre usa a cena "luz" (toggle físico) ──────────────
    if device_type == "light":
        # Pega cenas que NÃO são "desligar" (ou seja, scene.luz_*)
        luz_scenes = [s for s in scenes if "desligar" not in s.friendly_name.lower()]
        if luz_scenes:
            return [luz_scenes[0]]
        return non_scenes  # Fallback para entidade light.* real

    # ── VENTILADOR ────────────────────────────────────────────────
    if device_type == "fan":
        if action == "turn_off":
            # Desligar ventilador → usa scene.desligar_ventilador_*
            off_scenes = [s for s in scenes if "desligar" in s.friendly_name.lower()]
            if off_scenes:
                return [off_scenes[0]]
        else:
            # Ligar ventilador (genérico sem velocidade) → primeiro que não é "desligar"
            on_scenes = [s for s in scenes if "desligar" not in s.friendly_name.lower()]
            if on_scenes:
                return [on_scenes[0]]
        return non_scenes

    # ── VENTILAÇÃO / EXAUSTÃO ─────────────────────────────────────
    if device_type in ("ventilation", "exhaust"):
        # Só tem uma cena por tipo, retorna a primeira
        return [scenes[0]] if scenes else non_scenes

    # ── TV (IR Hub) ───────────────────────────────────────────────
    if device_type == "tv":
        # TV via IR é normalmente um botão único (toggle), então
        # usamos a primeira cena disponível independentemente do nome
        if scenes:
            return [scenes[0]]
        return non_scenes

    # ── GENÉRICO (tomada, etc.) ───────────────────────────────────
    if action == "turn_off":
        off_scenes = [s for s in scenes if "desligar" in s.friendly_name.lower()]
        if off_scenes:
            return [off_scenes[0]]
    else:
        on_scenes = [s for s in scenes if "desligar" not in s.friendly_name.lower()]
        if on_scenes:
            return [on_scenes[0]]

    return non_scenes if non_scenes else devices


# ═══════════════════════════════════════════════════════════════════════════
# EXECUÇÃO EM BACKGROUND (NÃO BLOQUEIA O PIPELINE)
# ═══════════════════════════════════════════════════════════════════════════

def _execute_ha_calls(jobs: List[Dict[str, Any]]):
    """Executa todas as chamadas ao Home Assistant em background.

    Cada job é um dict:
      entity_id: str
      action: str (turn_on | turn_off | toggle | activate_scene)
      kwargs: dict (brightness, speed, color, etc.)

    Retry: até 2 tentativas com backoff exponencial (100ms, 200ms).
    """
    from core.services.home_assistant import HomeAssistantManager

    ha = HomeAssistantManager()
    t0 = time.monotonic()
    ok_count = 0
    fail_count = 0

    for job in jobs:
        entity_id = job["entity_id"]
        action = job["action"]
        kwargs = job.get("kwargs", {})
        is_scene = entity_id.startswith("scene.")

        for attempt in range(3):
            try:
                if action == "activate_scene" or (action == "turn_on" and is_scene):
                    ha.activate_scene(entity_id)
                elif action == "turn_on":
                    ha.turn_on(entity_id, **kwargs)
                elif action == "turn_off":
                    if is_scene:
                        ha.activate_scene(entity_id)  # Cena de desligar = ativa a cena
                    else:
                        ha.turn_off(entity_id)
                elif action == "toggle":
                    ha.toggle(entity_id)
                elif action == "set_brightness":
                    ha.set_brightness(entity_id, kwargs.get("brightness", 128))
                elif action == "set_speed":
                    ha.set_speed(entity_id, kwargs.get("speed", "medium"))
                elif action == "set_color":
                    if hasattr(ha, "set_color"):
                        ha.set_color(entity_id, rgb_color=kwargs.get("color", [255, 255, 255]))
                    else:
                        ha.turn_on(entity_id)  # Fallback

                ok_count += 1
                break  # Sucesso, sem retry

            except Exception as e:
                if attempt < 2:
                    wait = 0.1 * (attempt + 1)
                    logger.warning(f"Retry {attempt+1}/2 para {entity_id}: {e} (aguardando {wait}s)")
                    time.sleep(wait)
                else:
                    logger.error(f"Falha permanente ao controlar {entity_id}: {e}")
                    fail_count += 1

    elapsed = (time.monotonic() - t0) * 1000
    logger.info(
        f"HA background: {ok_count} ok, {fail_count} falhas, "
        f"{len(jobs)} chamadas em {elapsed:.0f}ms"
    )


# ═══════════════════════════════════════════════════════════════════════════
# SKILL PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

class SmartHomeSkill:
    """Controla dispositivos de casa inteligente via Home Assistant."""

    def execute_tool(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> str | dict:
        """Ponto de entrada principal. Recebe argumentos do parser e contexto do pipeline."""

        action = arguments.get("action")
        device_type = arguments.get("device_type")
        device_name = arguments.get("device_name")
        target_room = arguments.get("target_room")
        scene_prefix = arguments.get("scene_prefix")

        db = context.get("db")
        fallback_room_id = context.get("room_id")

        if not db:
            return "Erro: banco de dados não disponível."

        if not action:
            return {"direct_response": "Não entendi qual ação você quer executar. Pode repetir?"}

        # ── Resolve o cômodo ──────────────────────────────────────────
        resolved_room_id = _resolve_room_id(db, target_room, fallback_room_id)
        if not resolved_room_id:
            return {"direct_response": "Não encontrei nenhum cômodo cadastrado."}

        logger.info(f"SmartHome: action={action}, type={device_type}, name={device_name}, room={resolved_room_id}")

        # ── Busca dispositivos ────────────────────────────────────────
        devices = _resolve_devices(db, resolved_room_id, device_type, device_name)

        if not devices:
            # Tenta sem device_name (pode ser que "ventilador 3" não esteja exato)
            if device_name:
                devices = _resolve_devices(db, resolved_room_id, device_type, None)

            if not devices:
                logger.warning(f"Nenhum dispositivo encontrado: room={resolved_room_id}, type={device_type}, name={device_name}")
                return {"direct_response": "Ok."}

        # ── Seleciona os melhores dispositivos (cena vs entidade) ─────
        selected = _pick_best_device(devices, action, device_name, device_type)

        if not selected:
            logger.warning(f"Nenhum dispositivo selecionado após filtragem: room={resolved_room_id}")
            return {"direct_response": "Ok."}

        # ── Monta os jobs para execução em background ─────────────────
        jobs = []
        for dev in selected:
            is_scene = dev.entity_id.startswith("scene.")

            if action == "turn_off" and is_scene:
                # Cena de desligar: ativamos a cena (que internamente desliga)
                jobs.append({
                    "entity_id": dev.entity_id,
                    "action": "activate_scene",
                })
            elif action == "turn_on" and is_scene:
                jobs.append({
                    "entity_id": dev.entity_id,
                    "action": "activate_scene",
                })
            else:
                jobs.append({
                    "entity_id": dev.entity_id,
                    "action": action,
                    "kwargs": {
                        k: v for k, v in {
                            "brightness": arguments.get("brightness"),
                            "speed": arguments.get("speed"),
                            "color": arguments.get("color"),
                        }.items() if v is not None
                    },
                })

        logger.info(f"SmartHome: despachando {len(jobs)} job(s) em background: "
                     f"{[j['entity_id'] for j in jobs]}")

        # ── Dispara em background (não bloqueia!) ─────────────────────
        threading.Thread(target=_execute_ha_calls, args=(jobs,), daemon=True).start()

        return {"direct_response": "Ok."}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS DE TRADUÇÃO (usados por outros módulos)
# ═══════════════════════════════════════════════════════════════════════════

def _translate_action(action: str) -> str:
    mapping = {
        "turn_on": "Liguei",
        "turn_off": "Desliguei",
        "toggle": "Alternei",
        "set_brightness": "Ajustei o brilho de",
        "set_color": "Mudei a cor de",
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
        "ventilation": "ventilação",
        "exhaust": "exaustão",
    }
    return mapping.get(dt, dt)
