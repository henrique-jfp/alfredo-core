import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Any
from core.brain.skills.base import Skill
from core.brain.memory import models

logger = logging.getLogger("alfredo.skills.music")
CACHE_PATH = os.path.join(os.getcwd(), ".spotify_cache")

class MusicSkill(Skill):
    @property
    def name(self) -> str:
        return "MusicSkill"

    def can_handle(self, intent: str, text: str) -> bool:
        return intent == "MUSIC"

    def _get_spotify(self, db):
        spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
        
        if not spotify or not spotify.client_id or not spotify.client_secret:
            return None
            
        auth_manager = SpotifyOAuth(
            client_id=spotify.client_id,
            client_secret=spotify.client_secret,
            redirect_uri="http://localhost:10001/api/spotify/callback",
            scope="user-modify-playback-state user-read-playback-state",
            cache_path=CACHE_PATH,
            open_browser=False
        )
        
        # Só consegue retornar a API se o token já estiver no cache (via /login do dashboard)
        token_info = auth_manager.get_cached_token()
        if not token_info:
            return None
            
        return spotipy.Spotify(auth_manager=auth_manager)

    def execute(self, text: str, context: Dict[str, Any]) -> str:
        db = context.get("db")
        if not db:
            return "Erro: sem acesso ao banco de dados."
            
        sp = self._get_spotify(db)
        if not sp:
            return "O Spotify não está autenticado. Conecte no painel do Dashboard usando o QR Code."
            
        text_lower = text.lower()
        
        try:
            if "pausar" in text_lower or "pausa" in text_lower or "pare a música" in text_lower or "parar música" in text_lower or "para de tocar" in text_lower:
                sp.pause_playback()
                return "Música pausada."
                
            elif "próxima" in text_lower or "proxima" in text_lower or "pular" in text_lower or "passar" in text_lower:
                sp.next_track()
                return "Tocando a próxima faixa."
                
            elif "voltar" in text_lower or "anterior" in text_lower or "começo" in text_lower:
                sp.previous_track()
                return "Voltando a música."
                
            elif "toca" in text_lower or "tocar" in text_lower or "toque" in text_lower:
                # Limpa a string para encontrar o que o usuário quer tocar
                term = text_lower.replace("alfredo", "").replace("tocar", "").replace("toca", "").replace("toque", "").replace("no spotify", "").replace("uma música do", "").replace("uma música da", "").strip()
                
                if not term or term == "uma música":
                    # Se apenas mandou tocar sem termo, tenta dar play no que estiver pausado
                    sp.start_playback()
                    return "Retomando a música."
                    
                logger.info(f"Buscando no Spotify por: {term}")
                results = sp.search(q=term, limit=1, type='track,artist')
                
                # Tenta achar uma música primeiro
                if results['tracks']['items']:
                    track_uri = results['tracks']['items'][0]['uri']
                    track_name = results['tracks']['items'][0]['name']
                    artist_name = results['tracks']['items'][0]['artists'][0]['name']
                    sp.start_playback(uris=[track_uri])
                    return f"Tocando {track_name}, de {artist_name}."
                # Se não achar música, tenta achar um artista
                elif results['artists']['items']:
                    artist_uri = results['artists']['items'][0]['uri']
                    artist_name = results['artists']['items'][0]['name']
                    sp.start_playback(context_uri=artist_uri)
                    return f"Tocando músicas de {artist_name}."
                else:
                    return f"Desculpe, não encontrei {term} no Spotify."
                    
            return "O que você quer que eu faça com a música?"
            
        except spotipy.exceptions.SpotifyException as e:
            logger.error(f"Erro na API do Spotify: {e}")
            if e.http_status == 404:
                return "Não encontrei nenhum dispositivo ativo. Abra o Spotify no seu celular ou computador e tente de novo."
            elif e.http_status == 403:
                return "Não tenho permissão para controlar a música. Verifique se a sua conta tem o Spotify Premium."
            return "Desculpe, tive um problema ao me comunicar com o servidor do Spotify."
        except Exception as e:
            logger.error(f"Erro interno MusicSkill: {e}")
            return "Desculpe, deu um erro inesperado ao controlar a música."
