import json
import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

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
        
        logger.info(f"Executando DreamSkill -> themes: {themes}, interpretation: {interpretation[:30]}...")
        
        db = context.get("db")
        room_id = context.get("room_id", "default")
        
        if db and interpretation:
            from core.brain.memory import models
            
            # Save the dream log to the DB
            dream_log = models.DreamLog(
                raw_text="", # We don't get the raw text here directly, but the interpretation and themes are the core
                themes=json.dumps(themes),
                interpretation=interpretation,
                room_id=room_id
            )
            db.add(dream_log)
            db.commit()
            logger.info("Sonho salvo no banco de dados.")

        instruction = (
            f"O diário de sonhos foi salvo com sucesso com os temas: {', '.join(themes)}. "
            f"Fale a seguinte interpretação de forma mística, serena e poética (sem dizer que está lendo): '{interpretation}'"
        )
            
        return {
            "internal_instruction": instruction,
            "status": "success"
        }
