import json
import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.dream")

class DreamSkill(Skill):

    @property
    def name(self) -> str:
        return "DreamSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "DREAM"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Tive um problema ao processar seu sonho."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        themes = kwargs.get("themes", [])
        interpretation = kwargs.get("interpretation", "")
        raw_text = kwargs.get("raw_text", "")

        logger.info(f"DreamSkill -> themes: {themes}, interpretation: {interpretation[:50]}...")

        db = context.get("db")
        room_id = context.get("room_id", "default")

        saved = False
        if db and interpretation and raw_text:
            try:
                from core.brain.memory import models

                dream_log = models.DreamLog(
                    raw_text=raw_text,
                    themes=json.dumps(themes) if isinstance(themes, list) else "[]",
                    interpretation=interpretation,
                    room_id=room_id
                )
                db.add(dream_log)
                db.commit()
                saved = True
                logger.info("Sonho salvo no banco de dados.")
            except Exception as e:
                logger.error(f"Erro ao salvar sonho no DB: {e}")

        if saved:
            msg = f"Salvei seu sonho no diário. {interpretation}"
        else:
            msg = interpretation if interpretation else "Conte-me mais sobre o sonho para eu interpretar."

        return {
            "status": "success",
            "direct_response": msg
        }
