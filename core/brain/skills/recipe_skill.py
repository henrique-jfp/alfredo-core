import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

class RecipeSkill(Skill):
    
    @property
    def name(self) -> str:
        return "RecipeSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "RECIPE"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para qual prato você gostaria da receita?"

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "recipe")
        query = kwargs.get("query", "")
        
        logger.info(f"Executando RecipeSkill -> action: {action}, query: {query}")
        
        if action == "recipe":
            instruction = (
                f"O usuário pediu a receita de: {query}. "
                f"Assuma a persona de um Chef de Cozinha amigável. "
                f"Sua resposta DEVE conter os ingredientes e APENAS O PASSO 1 do modo de preparo. "
                f"No final, peça para o usuário avisar quando terminar para ler o próximo passo. "
                f"NÃO gere todos os passos de uma vez!"
            )
        else:
            instruction = (
                f"O usuário perguntou sobre harmonização de vinhos e comidas envolvendo: {query}. "
                f"Assuma a persona de um Sommelier sofisticado e dê uma sugestão breve, citando uvas e queijos/carnes que combinam."
            )
            
        return {
            "internal_instruction": instruction,
            "status": "success"
        }
