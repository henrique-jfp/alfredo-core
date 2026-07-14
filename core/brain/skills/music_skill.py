import os
import re
import logging
from spotipy.exceptions import SpotifyException
from typing import Dict, Any, Optional
from core.brain.skills.base import Skill
from core.services import spotify_service, youtube_service

logger = logging.getLogger("alfredo.skills.music")

_COMMAND_VERBS = (
    r'\b(tocar|toca|toque|tocou|tocando|buscar|busca|procure|procurar|'
    r'coloque|colocar|ponha|passar|pular|próxima|proxima|voltar|anterior|'
    r'pausar|pausa|para de tocar|pare a música|parar música|retomar|continue|continua)\b'
)
_FILLER_PREFIX = (
    r'\b(no spotify|no\s+spotify|uma\s+música\s+(do|da)|um\s+som\s+(do|da)|'
    r'a\s+música\s+|a\s+faixa\s+|no\s+spotify)\b'
)


class MusicSkill(Skill):

    @property
    def name(self) -> str:
        return "MusicSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MUSIC"

    def _clean_search_term(self, text: str) -> str:
        term = text.lower()
        term = re.sub(r'\balfredo\b', '', term)
        term = re.sub(_COMMAND_VERBS, '', term)
        term = re.sub(_FILLER_PREFIX, '', term)
        term = re.sub(r'\s+', ' ', term).strip()
        return term

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        if not db:
            return "Erro: sem acesso ao banco de dados."

        sp = spotify_service.get_spotify_client(db)
        if not sp:
            return "O Spotify não está autenticado. Conecte no painel do Dashboard usando o QR Code."

        text_lower = text.lower()

        try:
            device_id = spotify_service.get_best_device(sp)

            if any(w in text_lower for w in ["pausar", "pausa", "pare a música", "parar música", "para de tocar", "parou"]):
                spotify_service.control_playback(sp, "pause", device_id)
                return "Música pausada."

            if any(w in text_lower for w in ["retomar", "continue", "continua", "voltar a tocar"]):
                spotify_service.control_playback(sp, "resume", device_id)
                return "Retomando a música."

            if any(w in text_lower for w in ["próxima", "proxima", "pular", "passar", "avançar"]):
                spotify_service.control_playback(sp, "next", device_id)
                return "Tocando a próxima faixa."

            if any(w in text_lower for w in ["voltar", "anterior", "começo", "início", "inicio"]):
                spotify_service.control_playback(sp, "previous", device_id)
                return "Voltando à faixa anterior."

            if any(w in text_lower for w in ["toca", "tocar", "toque", "buscar", "busca", "procure", "procurar", "coloque"]):
                term = self._clean_search_term(text)

                if not term:
                    spotify_service.control_playback(sp, "resume", device_id)
                    return "Retomando a música."

                logger.info(f"Buscando no Spotify por: {term}")
                result = spotify_service.search_and_play(sp, term, device_id) if device_id else None

                if result:
                    if result["type"] == "track":
                        return f"Tocando {result['name']}, de {result['artist']}."
                    elif result["type"] == "playlist":
                        return f"Tocando playlist {result['name']}."
                    return f"Tocando músicas de {result['name']}."
                else:
                    return f"Não encontrei {term} no Spotify."

            vol_match = re.search(r'volume\s+(\d+)', text_lower)
            if vol_match:
                vol = int(vol_match.group(1))
                spotify_service.control_playback(sp, "volume", device_id, vol)
                return f"Volume ajustado para {min(100, max(0, vol))}."

            return "O que você quer que eu faça com a música? Posso tocar, pausar, pular ou ajustar o volume."

        except SpotifyException as e:
            logger.error(f"Erro na API do Spotify: {e}")
            if e.http_status == 404:
                return "Não encontrei nenhum dispositivo ativo. Abra o Spotify no seu celular ou computador e tente de novo."
            elif e.http_status == 403:
                return "Não tenho permissão para controlar a música. Verifique se a sua conta tem o Spotify Premium."
            return "Desculpe, tive um problema ao me comunicar com o servidor do Spotify."
        except Exception as e:
            logger.error(f"Erro interno MusicSkill: {e}")
            return "Desculpe, deu um erro inesperado ao controlar a música."

    def _fallback_to_yt(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ws_tasks = context.get("ws_tasks")
        device_id = context.get("device_id")
        if not ws_tasks or not device_id:
            logger.warning("Fallback YT ignorado: contexto sem ws_tasks ou device_id")
            return {
                "direct_response": "Não encontrei dispositivos online no Spotify.",
                "status": "fail"
            }

        logger.info(f"Fazendo fallback para YouTube com a busca: {query}")
        result = youtube_service.search_audio(query, is_live=False)
        if result:
            url = result.get("url")
            title = result.get("title", query)
            if url:
                ws_tasks.append({
                    "device_id": device_id,
                    "payload": {
                        "type": "play_audio",
                        "url": url
                    }
                })
                return {"direct_response": f"Tocando {title} diretamente no alto-falante.", "status": "success"}

        return {
            "direct_response": "Não encontrei dispositivos online no Spotify, e também houve uma falha ao tentar reproduzir via YouTube.",
            "status": "fail"
        }

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        if not db:
            return {"error": "Banco de dados indisponível"}

        sp = spotify_service.get_spotify_client(db)
        if not sp:
            return {"error": "Spotify não autenticado. Conecte no painel do Dashboard."}

        action = kwargs.get("action", "play")
        query = kwargs.get("query", "").strip()

        try:
            device_id = spotify_service.get_best_device(sp)

            if action in ("pause", "stop"):
                if not device_id:
                    ws_tasks = context.get("ws_tasks")
                    device_id_ctx = context.get("device_id")
                    if ws_tasks and device_id_ctx:
                        ws_tasks.append({
                            "device_id": device_id_ctx,
                            "payload": {"type": "stop_audio"}
                        })
                    return {"direct_response": "Música parada.", "status": "success"}
                spotify_service.control_playback(sp, "pause", device_id)
                return {"direct_response": "Música pausada.", "status": "success"}

            elif action == "resume":
                if not device_id:
                    return {"error": "Nenhum dispositivo tocando."}
                spotify_service.control_playback(sp, "resume", device_id)
                return {"direct_response": "Retomando a música.", "status": "success"}

            elif action == "next":
                if not device_id:
                    return {"error": "Nenhum dispositivo tocando."}
                spotify_service.control_playback(sp, "next", device_id)
                return {"direct_response": "Tocando a próxima faixa.", "status": "success"}

            elif action == "previous":
                if not device_id:
                    return {"error": "Nenhum dispositivo tocando."}
                spotify_service.control_playback(sp, "previous", device_id)
                return {"direct_response": "Voltando à faixa anterior.", "status": "success"}

            elif action == "search":
                if not query:
                    if not device_id:
                        return {"error": "O que você gostaria de ouvir?"}
                    spotify_service.control_playback(sp, "resume", device_id)
                    return {"direct_response": "Retomando a música.", "status": "success"}

                if not device_id:
                    return self._fallback_to_yt(query, context)

                result = spotify_service.search_and_play(sp, query, device_id)
                if result:
                    if result["type"] == "track":
                        return {
                            "direct_response": f"Tocando {result['name']}, de {result['artist']}.",
                            "track": result['name'],
                            "artist": result['artist'],
                            "status": "success"
                        }
                    elif result["type"] == "playlist":
                        return {
                            "direct_response": f"Tocando playlist {result['name']}.",
                            "playlist": result['name'],
                            "status": "success"
                        }
                    return {
                        "direct_response": f"Tocando músicas de {result['name']}.",
                        "artist": result['name'],
                        "status": "success"
                    }

                return {"direct_response": f"Não encontrei {query} no Spotify.", "status": "fail"}

            elif action == "volume":
                if not device_id:
                    return {"error": "Nenhum dispositivo ativo."}
                vol = kwargs.get("volume", 50)
                spotify_service.control_playback(sp, "volume", device_id, vol)
                return {"direct_response": f"Volume ajustado para {vol}.", "status": "success"}

            return {"error": "Ação desconhecida. Use: pause, resume, next, previous, search ou volume."}

        except SpotifyException as e:
            logger.error(f"Erro no Spotify execute_tool: {e}")
            if e.http_status == 404:
                if action == "search":
                    return self._fallback_to_yt(query, context)
                return {"error": "Nenhum dispositivo ativo encontrado. Abra o Spotify em algum aparelho."}
            return {"error": "Erro de comunicação com o Spotify."}
        except Exception as e:
            logger.error(f"Erro inesperado execute_tool: {e}")
            return {"error": "Erro inesperado ao controlar a música."}
