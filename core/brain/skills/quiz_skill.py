import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.quiz")

MAX_QUESTIONS = 10

class QuizSkill(Skill):

    @property
    def name(self) -> str:
        return "QuizSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "QUIZ"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        return "Para iniciar o quiz, diga o tema que você deseja estudar."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "start")
        subject = kwargs.get("subject", "").strip()
        difficulty = kwargs.get("difficulty", "").strip()
        score = int(kwargs.get("score", 0))
        questions_count = int(kwargs.get("questions_count", 0))
        max_questions = int(kwargs.get("max_questions", MAX_QUESTIONS))

        if action == "start":
            if not subject:
                return {
                    "direct_response": "Qual assunto você quer estudar? Pode ser matemática, geografia, história, ciências...",
                    "status": "fail"
                }
            if not difficulty:
                difficulty = "criança de 9 anos"

            session = {
                "params": {
                    "subject": subject,
                    "difficulty": difficulty,
                    "score": 0,
                    "questions_count": 0,
                    "max_questions": max_questions
                }
            }
            return {
                "internal_instruction": (
                    f"O usuário quer iniciar um quiz sobre {subject}. Nível: {difficulty}. "
                    f"Seja um professor animado e faça a PRIMEIRA PERGUNTA agora. "
                    f"Regras do quiz:\n"
                    f"1. Após CADA resposta do usuário, avalie (certo/errado) e informe o placar.\n"
                    f"2. Na MESMA resposta, faça a PRÓXIMA pergunta.\n"
                    f"3. Junto com a pergunta, chame manage_quiz(action='update', "
                    f"score=ACERTOS, questions_count=TOTAL, subject='{subject}', "
                    f"difficulty='{difficulty}', max_questions={max_questions}) "
                    f"para salvar o placar.\n"
                    f"4. Após {max_questions} perguntas, encerre chamando manage_quiz(action='stop') "
                    f"e dê o resultado final com a pontuação.\n"
                    f"5. Se o usuário quiser parar antes, encerre também."
                ),
                "status": "success",
                "session": session
            }

        elif action == "update":
            session = {
                "params": {
                    "subject": subject,
                    "difficulty": difficulty,
                    "score": score,
                    "questions_count": questions_count,
                    "max_questions": max_questions
                }
            }
            return {
                "direct_response": f"Placar salvo: {score} acertos em {questions_count} perguntas.",
                "status": "success",
                "session": session
            }

        else:
            return {
                "status": "success",
                "session": {"end": True},
                "direct_response": (
                    f"Quiz encerrado! "
                    f"{f'Você fez {score} acertos em {questions_count} perguntas. ' if questions_count > 0 else ''}"
                    f"Foi muito divertido jogar com você. Volte sempre que quiser aprender mais."
                )
            }
