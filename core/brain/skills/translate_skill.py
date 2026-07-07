import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

class TranslateSkill(Skill):
    
    @property
    def name(self) -> str:
        return "TranslateSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "TRANSLATE"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        # Fallback caso a tool falhe
        return "Para traduções, me diga a frase e o idioma que você deseja."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "translate")
        target_language = kwargs.get("target_language", "inglês")
        text = kwargs.get("text", "")
        
        logger.info(f"Executando TranslateSkill -> action: {action}, language: {target_language}")
        
        if action == "lesson":
            instruction = (
                f"O usuário quer uma mini-aula rápida de 3 a 5 palavras ou frases úteis em {target_language}. "
                f"Tema: {text if text else 'tópicos do dia a dia'}. "
                f"Forneça a palavra no idioma usando a tag <lang=\"LOCALE\">palavra</lang> (ex: <lang=\"en-US\">hello</lang>), o significado em português e o contexto de uso. "
                f"Fale de forma natural, como um tutor de idiomas, e sem emojis."
            )
        else:
            instruction = (
                f"O usuário quer traduzir a frase '{text}' para {target_language}. "
                f"Forneça a tradução exata utilizando OBRIGATORIAMENTE a tag <lang=\"LOCALE\">tradução</lang> para o trecho traduzido (ex: <lang=\"en-US\">I love you</lang> ou <lang=\"ja-JP\">Aishiteru</lang>). "
                f"NÃO ESCREVA A PRONÚNCIA. O sistema de voz fará a leitura perfeitamente através da tag <lang>. "
                f"Seja direto e natural. Sem emojis."
            )
            
        return {
            "internal_instruction": instruction,
            "status": "success"
        }
