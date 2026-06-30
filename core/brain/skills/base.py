from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class Skill(ABC):
    """
    Interface base para todas as Habilidades (Skills) do Alfredo.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Retorna o nome da skill."""
        pass

    @abstractmethod
    def can_handle(self, intent: str, text: str) -> bool:
        """
        Retorna True se esta skill for capaz de lidar com a intenção/texto fornecidos.
        """
        pass

    @abstractmethod
    def execute(self, text: str, context: Dict[str, Any]) -> str:
        """
        Executa a lógica da skill e retorna o texto da resposta que será falada pelo Alfredo.
        
        Args:
            text: O texto original falado pelo usuário.
            context: Dicionário contendo estado extra (ex: device_id, room_id).
            
        Returns:
            str: O texto de resposta.
        """
        pass
