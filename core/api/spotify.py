import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from core.brain.memory import models
from core.brain.memory.database import get_db

router = APIRouter(prefix="/api/spotify", tags=["spotify"])
logger = logging.getLogger("alfredo.spotify")

CACHE_PATH = os.path.join(os.getcwd(), ".spotify_cache")

def get_spotify_oauth(db: Session, request: Request):
    spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
    
    if not spotify or not spotify.client_id or not spotify.client_secret:
        return None
        
    # Usa o IP que o usuário (celular) está acessando como redirect_uri dinâmico
    host = request.headers.get("host", "localhost:10001")
    redirect_uri = f"http://{host}/api/spotify/callback"
        
    return SpotifyOAuth(
        client_id=spotify.client_id,
        client_secret=spotify.client_secret,
        redirect_uri=redirect_uri,
        scope="user-modify-playback-state user-read-playback-state",
        cache_path=CACHE_PATH,
        open_browser=False
    )

@router.get("/login")
def login(request: Request, db: Session = Depends(get_db)):
    """Redireciona o usuário para a página de login do Spotify."""
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        raise HTTPException(status_code=500, detail="Chaves do Spotify não configuradas no Banco de Dados")
        
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)

@router.get("/callback")
def callback(code: str, request: Request, db: Session = Depends(get_db)):
    """Recebe o código do Spotify e gera o token de acesso."""
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        raise HTTPException(status_code=500, detail="Chaves do Spotify não configuradas.")
        
    try:
        sp_oauth.get_access_token(code)
        
        # Atualiza status no BD para conectado
        spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
        if spotify:
            spotify.is_connected = True
            db.commit()
            
        return {"status": "success", "message": "Spotify conectado com sucesso! Você já pode fechar esta aba no celular e olhar para a tela do computador."}
    except Exception as e:
        logger.error(f"Erro no callback do Spotify: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar token.")
