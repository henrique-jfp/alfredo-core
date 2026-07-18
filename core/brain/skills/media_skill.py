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
                    title = r.get("title", "Título não disponível")
                    rating = r.get("rating", "N/A")
                    # Usa 'overview' como sinopse fallback, pois nem todas as APIs retornam 'synopsis'
                    synopsis = r.get("synopsis") or r.get("overview", "Sinopse não disponível")
                    # Tenta obter a plataforma de streaming; se não houver, usa 'Não informado'
                    watch = r.get("where_to_watch") or r.get("streaming_platforms", "Não informado")
                    lines.append(f"{title} - Nota: {rating}\nSinopse: {synopsis}\nOnde assistir: {watch}")
                data["direct_response"] = "\n\n".join(lines)
            elif "message" in data:
                data["direct_response"] = data["message"]
            else:
                data["direct_response"] = "Nenhum resultado encontrado."
            
            # Loga o conteúdo gerado para depuração (mantém o log dentro do limite de tamanho)
            logger.debug(f"MediaSkill direct_response gerado: {data['direct_response'][:200]}")
            return data
        except Exception as e:
            logger.error(f"Erro no execute_tool do MediaSkill: {e}")
            return {"error": str(e)}
