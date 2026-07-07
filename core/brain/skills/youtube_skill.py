import logging
import yt_dlp
import re
from typing import Dict, Any
from core.brain.skills.base import Skill

logger = logging.getLogger("alfredo.skills.youtube")

class YouTubeSkill(Skill):
    @property
    def name(self) -> str:
        return "YouTubeSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "YOUTUBE"

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        text_lower = text.lower()
        
        # Limpar o texto para achar a busca real
        # Ex: "tocar o video do jovem nerd no youtube" -> "jovem nerd"
        # "coloca a live da cnn" -> "cnn"
        
        remove_words = [
            "reproduza", "reproduzir", "tocar", "toque", "coloque", "coloca", "rola", "rolar",
            "abrir", "canal", "ao vivo", "no youtube", "na twitch"
        ]
        
        query = text_lower
        for w in remove_words:
            # Usando regex para remover a palavra inteira e não partes dela
            query = re.sub(rf'\b{w}\b', '', query).strip()
            
        # Se a pessoa só falou "tocar no youtube", usamos o texto inteiro como fallback
        if not query:
            query = text_lower
            
        return self._play(query, "ao vivo" in text_lower, context)

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        query = kwargs.get("query", "").strip()
        is_live = kwargs.get("is_live", False)

        if not query:
            return {
                "error": "Nenhuma busca informada.",
                "direct_response": "O que você gostaria de ouvir no YouTube?"
            }

        result_text = self._play(query, is_live, context)
        return {"direct_response": result_text, "status": "success"}

    def _play(self, query: str, is_live: bool, context: Dict[str, Any]) -> str:
        if not query:
            return "O que você gostaria de ouvir no YouTube?"

        logger.info(f"Buscando áudio no YouTube para a query: '{query}' (live={is_live})")

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }

        try:
            if is_live:
                import requests
                url = "https://www.youtube.com/youtubei/v1/search"
                payload = {
                    "context": {
                        "client": {
                            "clientName": "WEB",
                            "clientVersion": "2.20210721.00.00"
                        }
                    },
                    "query": query,
                    "params": "EgJAAQ=="
                }

                try:
                    response = requests.post(url, json=payload, timeout=5)
                    data = response.json()

                    import unicodedata

                    def normalize_text(s):
                        if not s: return ""
                        s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
                        return s.replace(" ", "").lower()

                    candidates = []
                    contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
                    for content in contents:
                        items = content.get('itemSectionRenderer', {}).get('contents', [])
                        for item in items:
                            video = item.get('videoRenderer', {})
                            if video:
                                v_id = video.get('videoId')
                                title = video.get('title', {}).get('runs', [{}])[0].get('text', '').lower()
                                uploader = video.get('ownerText', {}).get('runs', [{}])[0].get('text', '').lower()
                                if v_id:
                                    candidates.append({"id": v_id, "title": title, "uploader": uploader})

                    video_id = None
                    if candidates:
                        norm_query = normalize_text(query)
                        best_match = None
                        best_score = -1

                        for c in candidates:
                            score = 0
                            norm_uploader = normalize_text(c['uploader'])
                            norm_title = normalize_text(c['title'])

                            if norm_query and norm_query in norm_uploader:
                                score += 100
                            if norm_query and norm_query in norm_title:
                                score += 20

                            if score > best_score:
                                best_score = score
                                best_match = c

                        if best_match and best_score > 0:
                            video_id = best_match["id"]
                        else:
                            video_id = None

                    if not video_id:
                        return "Não encontrei nenhuma transmissão ao vivo acontecendo neste momento para esse canal."

                    search_url = f"https://www.youtube.com/watch?v={video_id}"
                except Exception as req_err:
                    logger.error(f"Erro ao buscar live na API do YouTube: {req_err}")
                    return "Ocorreu um erro ao buscar transmissões ao vivo."
            else:
                search_url = f"ytsearch1:{query}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)

                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                else:
                    entry = info

                if entry:
                    title = entry.get('title', 'Vídeo Desconhecido')
                    stream_url = entry.get('url')
                    if "ws_tasks" in context and "device_id" in context:
                        context["ws_tasks"].append({
                            "device_id": context["device_id"],
                            "payload": {
                                "type": "play_audio",
                                "url": stream_url
                            }
                        })
                        logger.info(f"Link de áudio gerado para '{title}' (URL: {stream_url[:50]}...)")

                    return f"Tocando agora o áudio de: {title}."
                else:
                    return "Não encontrei nenhum vídeo ou live com esse nome."

        except Exception as e:
            logger.error(f"Erro no yt-dlp: {e}")
            return "Ocorreu um erro ao tentar acessar o YouTube no momento."
