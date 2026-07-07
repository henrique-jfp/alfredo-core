import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.recipe")

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
        step = int(kwargs.get("step", 1))

        logger.info(f"RecipeSkill -> action: {action}, query: {query}, step: {step}")

        if action == "recipe":
            if not query:
                return {
                    "direct_response": "Qual prato você quer aprender? Posso ensinar risoto, lasanha, strogonoff...",
                    "status": "fail"
                }
            instruction = (
                f"O usuário pediu a receita de: {query}. "
                f"Assuma a persona de um Chef de Cozinha amigável. "
                f"Sua resposta DEVE conter os ingredientes e APENAS O PASSO 1 do modo de preparo. "
                f"Regras:\n"
                f"1. Após CADA passo, na MESMA resposta, chame "
                f"manage_recipe(action='next_step', query='{query}', step=2) "
                f"para salvar o progresso.\n"
                f"2. Quando o usuário pedir o próximo passo, informe o passo seguinte "
                f"e na MESMA resposta chame manage_recipe(action='next_step', "
                f"query='{query}', step={step + 1}).\n"
                f"3. Ao final (último passo ou usuário agradecer/encerrar), "
                f"chame manage_recipe(action='finish')."
            )
            session = {
                "params": {"query": query, "step": 1}
            }
            return {
                "internal_instruction": instruction,
                "status": "success",
                "session": session
            }

        elif action == "next_step":
            session = {
                "params": {"query": query, "step": step}
            }
            return {
                "direct_response": f"Passo {step - 1} concluído. Próximo passo: {step}.",
                "status": "success",
                "session": session
            }

        elif action == "finish":
            return {
                "status": "success",
                "session": {"end": True},
                "direct_response": "Receita encerrada! Bom apetite!"
            }

        elif action == "pairing":
            return {
                "internal_instruction": (
                    f"O usuário perguntou sobre harmonização de vinhos e comidas envolvendo: {query}. "
                    f"Assuma a persona de um Sommelier sofisticado e dê uma sugestão breve, "
                    f"citando uvas e queijos/carnes que combinam."
                ),
                "status": "success",
                "session": {"end": True}
            }

        else:
            return {
                "status": "success",
                "session": {"end": True},
                "direct_response": "Ação desconhecida. Como posso ajudar?"
            }
