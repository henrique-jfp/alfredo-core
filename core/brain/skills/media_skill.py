import logging
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills")

class MediaSkill(Skill):
    
    @property
    def name(self) -> str:
        return "MediaSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MEDIA"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        # Fallback se não usar a Tool
        return "Para recomendar filmes ou séries, preciso de detalhes sobre o que você quer assistir."

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        from core.services.media_service import discover_media
        
        media_type = kwargs.get("media_type", "movie")
        genre = kwargs.get("genre")
        year = kwargs.get("decade_or_year")
        
        try:
            return discover_media(media_type=media_type, genre=genre, year=year)
        except Exception as e:
            logger.error(f"Erro no execute_tool do MediaSkill: {e}")
            return {"error": str(e)}
