import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

class MemorySkill(Skill):
    
    @property
    def name(self) -> str:
        return "MemorySkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MEMORY"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Não consegui salvar essa memória."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        fact = kwargs.get("fact", "")
        
        logger.info(f"Executando MemorySkill -> guardando fato: {fact}")
        
        db = context.get("db")
        room_id = context.get("room_id", "default")
        
        if db and fact:
            from core.brain.memory import models
            
            memory = models.MemoryFact(
                fact=fact,
                room_id=room_id
            )
            db.add(memory)
            db.commit()
            logger.info("Fato salvo na Memória de Longo Prazo.")

        return {
            "status": "success",
            "direct_response": f"Entendido! Guardei na memória que {fact.lower()}. Não vou esquecer."
        }
