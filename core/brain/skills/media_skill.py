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
            data = discover_media(media_type=media_type, genre=genre, year=year)
            if "results" in data and data["results"]:
                lines = []
                for r in data["results"]:
                    watch = r.get("where_to_watch", "")
                    lines.append(f"{r['title']} (nota {r['rating']})")
                data["direct_response"] = f"Recomendo: {'; '.join(lines)}."
            elif "message" in data:
                data["direct_response"] = data["message"]
            return data
        except Exception as e:
            logger.error(f"Erro no execute_tool do MediaSkill: {e}")
            return {"error": str(e)}
