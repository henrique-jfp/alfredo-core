import re
import logging
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.services import youtube_service

logger = logging.getLogger("alfredo.skills.youtube")


class YouTubeSkill(Skill):
    @property
    def name(self) -> str:
        return "YouTubeSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "YOUTUBE"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        text_lower = text.lower()

        remove_words = [
            "reproduza", "reproduzir", "tocar", "toque", "coloque", "coloca",
            "rola", "rolar", "abrir", "canal", "ao vivo", "no youtube",
        ]
        query = text_lower
        for w in remove_words:
            query = re.sub(rf'\b{w}\b', '', query).strip()

        if not query:
            query = text_lower

        is_live = "ao vivo" in text_lower
        if "parar" in text_lower or "para" in text_lower or "stop" in text_lower:
            return self._stop(context)

        result_text = self._play(query, is_live, context)
        return result_text

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action = kwargs.get("action", "play")

        if action == "stop":
            result_text = self._stop(context)
            return {"direct_response": result_text, "status": "success"}

        query = kwargs.get("query", "").strip()
        if not query:
            return {
                "error": "Nenhuma busca informada.",
                "direct_response": "O que você gostaria de ouvir no YouTube?"
            }

        is_live = kwargs.get("is_live", False)
        result_text = self._play(query, is_live, context)
        return {"direct_response": result_text, "status": "success"}

    def _stop(self, context: Dict[str, Any]) -> str:
        ws_tasks = context.get("ws_tasks")
        device_id = context.get("device_id")
        if ws_tasks and device_id:
            ws_tasks.append({
                "device_id": device_id,
                "payload": {"type": "stop_audio"}
            })
            return "Áudio parado."
        return "Não há áudio tocando no momento."

    def _play(self, query: str, is_live: bool, context: Dict[str, Any]) -> str:
        if not query:
            return "O que você gostaria de ouvir no YouTube?"

        if youtube_service.is_ambiguous_query(query):
            return "Diga o nome do canal, música, vídeo ou live com mais detalhes."

        logger.info(f"Buscando áudio no YouTube para: '{query}' (live={is_live})")

        result = youtube_service.search_audio(query, is_live)
        if not result:
            return "Não encontrei nenhum vídeo ou live com esse nome."

        stream_url = result.get("url")
        title = result.get("title", "Vídeo Desconhecido")

        ws_tasks = context.get("ws_tasks")
        device_id = context.get("device_id")
        if ws_tasks and device_id and stream_url:
            ws_tasks.append({
                "device_id": device_id,
                "payload": {"type": "play_audio", "url": stream_url}
            })
            logger.info(f"Link de áudio gerado para '{title}'")
            return f"Tocando agora o áudio de: {title}."

        return "Não foi possível reproduzir o áudio no dispositivo."
