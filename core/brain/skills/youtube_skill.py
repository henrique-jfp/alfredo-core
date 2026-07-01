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
            # Se o usuário pediu explicitamente "ao vivo", usamos a API interna do YouTube para garantir o filtro de Live
            if "ao vivo" in text_lower:
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
                    "params": "EgJAAQ==" # Filtro exclusivo para transmissões "Ao Vivo"
                }
                
                try:
                    response = requests.post(url, json=payload, timeout=5)
                    data = response.json()
                    
                    import unicodedata
                    
                    def normalize_text(s):
                        if not s: return ""
                        # Remove acentos e espaços para comparação exata (ex: caze tv -> cazetv)
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
                            
                            # Se o nome do canal bate perfeitamente
                            if norm_query and norm_query in norm_uploader:
                                score += 100
                            # Se o título contém o nome buscado
                            if norm_query and norm_query in norm_title:
                                score += 20
                                
                            if score > best_score:
                                best_score = score
                                best_match = c
                                
                        # Se achou uma pontuação alta (indicando que é o canal certo)
                        if best_match and best_score > 0:
                            video_id = best_match["id"]
                        else:
                            # Se não deu match forte, não abre nada para não abrir canal errado
                            video_id = None
                            
                    if not video_id:
                        return "Não encontrei nenhuma transmissão ao vivo acontecendo neste momento para esse canal."
                        
                    search_url = f"https://www.youtube.com/watch?v={video_id}"
                except Exception as req_err:
                    logger.error(f"Erro ao buscar live na API do YouTube: {req_err}")
                    return "Ocorreu um erro ao buscar transmissões ao vivo."
            else:
                # Busca normal para vídeos gravados
                search_url = f"ytsearch1:{query}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                
                if 'entries' in info and len(info['entries']) > 0:
                    entry = info['entries'][0]
                else:
                    entry = info # Caso tenha sido URL direta (live), o dicionário já é o próprio vídeo
                    
                if entry:
                    title = entry.get('title', 'Vídeo Desconhecido')
                    stream_url = entry.get('url')
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
