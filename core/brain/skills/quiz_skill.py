import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

class QuizSkill(Skill):
    
    @property
    def name(self) -> str:
        return "QuizSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "QUIZ"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para iniciar o quiz, diga o tema que você deseja."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "start")
        subject = kwargs.get("subject", "conhecimentos gerais")
        difficulty = kwargs.get("difficulty", "criança de 9 anos")
        
        logger.info(f"Executando QuizSkill -> action: {action}, subject: {subject}, difficulty: {difficulty}")
        
        if action == "start":
            instruction = (
                f"O usuário quer iniciar um jogo de perguntas (Quiz) sobre {subject}. "
                f"O nível de dificuldade deve ser adaptado para: {difficulty}. "
                f"Assuma a persona de um professor ou apresentador de TV animado e divertido. "
                f"De as boas-vindas ao jogo, e FAÇA A PRIMEIRA PERGUNTA AGORA."
            )
        else:
            instruction = (
                "O usuário pediu para encerrar o Quiz. "
                "Despeça-se de forma amigável e diga que foi muito divertido jogar, encerrando o jogo."
            )
            
        return {
            "internal_instruction": instruction,
            "status": "success"
        }
