import os
import re
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from typing import Dict, Any, Optional
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.music")
CACHE_PATH = os.path.join(os.getcwd(), ".spotify_cache")

class MusicSkill(Skill):
    def __init__(self):
        self._spotify_client: Optional[spotipy.Spotify] = None
        self._last_creds_hash: Optional[int] = None

    @property
    def name(self) -> str:
        return "MusicSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MUSIC"

    def _get_spotify(self, db) -> Optional[spotipy.Spotify]:
        spotify = db.query(models.AppIntegration).filter(
            models.AppIntegration.app_name == "spotify"
        ).first()

        if not spotify or not spotify.client_id or not spotify.client_secret:
            return None

        # Cache: se credenciais não mudaram, reusa o client
        creds_hash = hash((spotify.client_id, spotify.client_secret))
        if self._spotify_client and self._last_creds_hash == creds_hash:
            return self._spotify_client

        redirect_uri = "http://127.0.0.1:10001/api/spotify/callback"

        auth_manager = SpotifyOAuth(
            client_id=spotify.client_id,
            client_secret=spotify.client_secret,
            redirect_uri=redirect_uri,
            scope="user-modify-playback-state user-read-playback-state",
            cache_path=CACHE_PATH,
            open_browser=False
        )

        token_info = auth_manager.get_cached_token()
        if not token_info:
            return None

        self._spotify_client = spotipy.Spotify(auth_manager=auth_manager)
        self._last_creds_hash = creds_hash
        return self._spotify_client

    def _clean_search_term(self, text: str) -> str:
        """Remove palavras de comando e artigos, mantendo só o termo de busca."""
        term = text.lower()
        # Remove wake word
        term = re.sub(r'\balfredo\b', '', term)
        # Remove verbos de comando
        term = re.sub(r'\b(tocar|toca|toque|tocou|tocando|buscar|busca|procure|procurar|coloque|colocar|ponha|passar|pular|próxima|proxima|voltar|anterior|pausar|pausa|para de tocar|pare a música|parar música|retomar|continue|continua)\b', '', term)
        # Remove "no spotify", "no Spotify", "uma música do", "uma música da", "um som de"
        term = re.sub(r'\b(no spotify|no\s+spotify|uma\s+música\s+(do|da)|um\s+som\s+(do|da)|a\s+música\s+|a\s+faixa\s+)\b', '', term)
        # Remove artigos, preposições curtas
        term = re.sub(r'\b(um|uma|uns|umas|o|a|os|as|do|da|dos|das|no|na|nos|nas|de|em|pra|pro|para)\b', '', term)
        # Limpa espaços múltiplos
        term = re.sub(r'\s+', ' ', term).strip()
        return term

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        if not db:
            return "Erro: sem acesso ao banco de dados."

        sp = self._get_spotify(db)
        if not sp:
            return "O Spotify não está autenticado. Conecte no painel do Dashboard usando o QR Code."

        text_lower = text.lower()

        try:
            device_id = self._get_best_device(sp)

            # Pausar
            if any(w in text_lower for w in ["pausar", "pausa", "pare a música", "parar música", "para de tocar", "parou"]):
                if device_id:
                    sp.pause_playback(device_id=device_id)
                else:
                    sp.pause_playback()
                return "Música pausada."

            # Retomar
            if any(w in text_lower for w in ["retomar", "continue", "continua", "voltar a tocar"]):
                if device_id:
                    sp.start_playback(device_id=device_id)
                else:
                    sp.start_playback()
                return "Retomando a música."

            # Próxima
            if any(w in text_lower for w in ["próxima", "proxima", "pular", "passar", "avançar", "avançar"]):
                if device_id:
                    sp.next_track(device_id=device_id)
                else:
                    sp.next_track()
                return "Tocando a próxima faixa."

            # Voltar
            if any(w in text_lower for w in ["voltar", "anterior", "começo", "início", "inicio"]):
                if device_id:
                    sp.previous_track(device_id=device_id)
                else:
                    sp.previous_track()
                return "Voltando à faixa anterior."

            # Tocar/buscar
            if any(w in text_lower for w in ["toca", "tocar", "toque", "buscar", "busca", "procure", "procurar", "coloque"]):
                term = self._clean_search_term(text)

                if not term:
                    if device_id:
                        sp.start_playback(device_id=device_id)
                    else:
                        sp.start_playback()
                    return "Retomando a música."

                logger.info(f"Buscando no Spotify por: {term}")
                results = sp.search(q=term, limit=1, type='track,artist')

                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    try:
                        if device_id:
                            sp.start_playback(device_id=device_id, context_uri=track['album']['uri'], offset={"uri": track['uri']})
                        else:
                            sp.start_playback(context_uri=track['album']['uri'], offset={"uri": track['uri']})
                    except:
                        if device_id:
                            sp.start_playback(device_id=device_id, uris=[track['uri']])
                        else:
                            sp.start_playback(uris=[track['uri']])
                    return f"Tocando {track['name']}, de {track['artists'][0]['name']}."

                elif results['artists']['items']:
                    artist = results['artists']['items'][0]
                    if device_id:
                        sp.start_playback(device_id=device_id, context_uri=artist['uri'])
                    else:
                        sp.start_playback(context_uri=artist['uri'])
                    return f"Tocando músicas de {artist['name']}."

                else:
                    return f"Não encontrei {term} no Spotify."

            # Volume
            vol_match = re.search(r'volume\s+(\d+)', text_lower)
            if vol_match:
                vol = int(vol_match.group(1))
                vol = max(0, min(100, vol))
                if device_id:
                    sp.volume(vol, device_id=device_id)
                else:
                    sp.volume(vol)
                return f"Volume ajustado para {vol}."

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
        logger.info(f"Fazendo fallback para YouTube com a busca: {query}")
        try:
            import yt_dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'extract_flat': False
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                if 'entries' in info and info['entries']:
                    entry = info['entries'][0]
                    url = entry.get('url')
                    title = entry.get('title', query)
                    if url and "ws_tasks" in context and "device_id" in context:
                        context["ws_tasks"].append({
                            "device_id": context["device_id"],
                            "payload": {
                                "type": "play_audio",
                                "url": url
                            }
                        })
                        return {"direct_response": f"Tocando {title} diretamente no alto-falante.", "status": "success"}
        except Exception as e:
            logger.error(f"Erro no fallback do YT: {e}")
        return {
            "error": "Nenhum dispositivo ativo encontrado no Spotify e falha ao buscar no YouTube.",
            "direct_response": "Não encontrei dispositivos online no Spotify, e também houve uma falha ao tentar reproduzir via YouTube."
        }

    def _get_best_device(self, sp) -> Optional[str]:
        devices = sp.devices()
        logger.info(f"SPOTIFY DEVICES ENCONTRADOS: {devices}")
        if not devices or not devices.get('devices'):
            return None
            
        # Prioridade 1: Alfredo Speaker
        for d in devices['devices']:
            if d.get('name') == 'Alfredo Speaker':
                logger.info(f"Encontrado Alfredo Speaker nativo: {d['id']}")
                return d['id']
                
        # Prioridade 2: Ativo
        for d in devices['devices']:
            if d.get('is_active'):
                return d['id']
                
        # Prioridade 3: Primeiro
        return devices['devices'][0]['id']

    def execute_tool(self, kwargs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        if not db:
            return {"error": "Banco de dados indisponível"}

        sp = self._get_spotify(db)
        if not sp:
            return {"error": "Spotify não autenticado. Conecte no painel do Dashboard."}

        action = kwargs.get("action", "play")
        query = kwargs.get("query", "").strip()

        try:
            device_id = self._get_best_device(sp)
            if not device_id:
                logger.warning("Nenhum dispositivo Spotify encontrado na conta!")

            if action == "pause" or action == "stop":
                if not device_id:
                    # Se não há device Spotify ativo, tente parar o fallback local via WebSocket
                    if "ws_tasks" in context and "device_id" in context:
                        context["ws_tasks"].append({
                            "device_id": context["device_id"],
                            "payload": {"type": "stop_audio"}
                        })
                    return {"direct_response": "Música parada.", "status": "success"}
                
                sp.pause_playback(device_id=device_id)
                return {"direct_response": "Música pausada.", "status": "success"}

            elif action == "resume":
                if not device_id: return {"error": "Nenhum dispositivo tocando."}
                sp.start_playback(device_id=device_id)
                return {"direct_response": "Retomando a música.", "status": "success"}

            elif action == "next":
                if not device_id: return {"error": "Nenhum dispositivo tocando."}
                sp.next_track(device_id=device_id)
                return {"direct_response": "Tocando a próxima faixa.", "status": "success"}

            elif action == "previous":
                if not device_id: return {"error": "Nenhum dispositivo tocando."}
                sp.previous_track(device_id=device_id)
                return {"direct_response": "Voltando à faixa anterior.", "status": "success"}

            elif action == "search":
                if not query:
                    if not device_id: return {"error": "O que você gostaria de ouvir?"}
                    sp.start_playback(device_id=device_id)
                    return {"direct_response": "Retomando a música.", "status": "success"}
                
                if not device_id:
                    # FALLBACK PARA YOUTUBE DIRETO NO ALTO-FALANTE!
                    return self._fallback_to_yt(query, context)

                results = sp.search(q=query, limit=1, type='track,artist')
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    try:
                        # Tenta usar o contexto do álbum para criar uma fila automática
                        sp.start_playback(
                            device_id=device_id, 
                            context_uri=track['album']['uri'], 
                            offset={"uri": track['uri']}
                        )
                    except:
                        # Fallback se o album context falhar
                        sp.start_playback(device_id=device_id, uris=[track['uri']])
                        
                    return {
                        "direct_response": f"Tocando {track['name']}, de {track['artists'][0]['name']}.",
                        "track": track['name'],
                        "artist": track['artists'][0]['name'],
                        "status": "success"
                    }
                elif results['artists']['items']:
                    artist = results['artists']['items'][0]
                    sp.start_playback(device_id=device_id, context_uri=artist['uri'])
                    return {
                        "direct_response": f"Tocando músicas de {artist['name']}.",
                        "artist": artist['name'],
                        "status": "success"
                    }
                return {"direct_response": f"Não encontrei {query} no Spotify.", "status": "fail"}

            elif action == "volume":
                if not device_id: return {"error": "Nenhum dispositivo ativo."}
                vol = kwargs.get("volume", 50)
                vol = max(0, min(100, int(vol)))
                sp.volume(vol, device_id=device_id)
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
