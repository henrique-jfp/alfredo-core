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
        
        # Verifica se quer o "último vídeo" para mudar o tipo de busca
        is_latest = False
        if "último vídeo" in text_lower or "ultimo video" in text_lower or "último" in text_lower or "ultimo" in text_lower:
            is_latest = True
            
        remove_words = [
            "reproduza", "reproduzir", "tocar", "toque", "coloque", "coloca", "rola", "rolar",
            "o último vídeo", "o ultimo video", "último vídeo", "ultimo video",
            "o vídeo", "o video", "um vídeo", "um video", "vídeo", "video",
            "a live", "live", "do canal", "canal", "do", "da", "de", "no", "youtube"
        ]
        
        query = text_lower
        for w in remove_words:
            # Usando regex para remover a palavra inteira e não partes dela
            query = re.sub(rf'\b{w}\b', '', query).strip()
            
        # Se a pessoa só falou "tocar no youtube", usamos o texto inteiro como fallback
        if not query:
            query = text_lower
            
        logger.info(f"Buscando áudio no YouTube para a query: '{query}'")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Evita baixar playlists inteiras caso caia numa
            'noplaylist': True, 
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_prefix = "ytsearchdate1:" if is_latest else "ytsearch1:"
                info = ydl.extract_info(f"{search_prefix}{query}", download=False)
                
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                    title = entry.get('title', 'Vídeo Desconhecido')
                    stream_url = entry.get('url')
                    
                    if not stream_url:
                        return f"Encontrei '{title}', mas não consegui extrair o link do áudio."
                    
                    # Envia para a fila do WebSocket para a placa tocar
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
