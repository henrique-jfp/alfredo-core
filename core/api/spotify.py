import os
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from core.brain.memory import models
from core.brain.memory.database import get_db

router = APIRouter(prefix="/api/spotify", tags=["spotify"])
logger = logging.getLogger("alfredo.spotify")

CACHE_PATH = os.path.join(os.getcwd(), ".spotify_cache")


def get_spotify_oauth(db: Session, request: Request = None):
    spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
    if not spotify or not spotify.client_id or not spotify.client_secret:
        return None
        
    if request:
        base_url = str(request.base_url).rstrip("/")
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto == "https" and base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://")
        redirect_uri = f"{base_url}/api/spotify/callback"
    else:
        redirect_uri = "https://alfredo.henriquedejesus.dev/api/spotify/callback"
        
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
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        raise HTTPException(status_code=500, detail="Chaves do Spotify não configuradas no Banco de Dados")
    auth_url = sp_oauth.get_authorize_url()
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(request: Request, code: str = None, state: str = None, error: str = None, db: Session = Depends(get_db)):
    if error:
        logger.error(f"Spotify retornou erro: {error}")
        return HTMLResponse(
            f"<html><body style='font-family:sans-serif;background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            f"<div style='text-align:center'><h1 style='color:#ef4444'>Autorização negada</h1>"
            f"<p>{error}</p>"
            f"<a href='/' style='color:#1DB954'>Voltar ao Dashboard</a></div></body></html>"
        )
    if not code:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h1 style='color:#ef4444'>Erro ao conectar</h1>"
            "<p>Nenhum código de autorização recebido do Spotify.</p>"
            "<a href='/' style='color:#1DB954'>Voltar ao Dashboard</a></div></body></html>"
        )
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        raise HTTPException(status_code=500, detail="Chaves do Spotify não configuradas.")
    try:
        sp_oauth.get_access_token(code)
        spotify = db.query(models.AppIntegration).filter(models.AppIntegration.app_name == "spotify").first()
        if spotify:
            spotify.is_connected = True
            db.commit()
        logger.info("Spotify conectado com sucesso via callback!")
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h1 style='color:#1DB954'>Spotify Conectado!</h1>"
            "<p>Você já pode fechar esta aba e voltar ao Dashboard.</p>"
            "<a href='/' style='color:#1DB954'>Voltar ao Dashboard</a></div></body></html>"
        )
    except Exception as e:
        logger.error(f"Erro no callback do Spotify: {e}")
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
            "<div style='text-align:center'><h1 style='color:#ef4444'>Erro ao conectar</h1>"
            f"<p>{e}</p></div></body></html>"
        )


@router.get("/now-playing")
def get_now_playing(request: Request, db: Session = Depends(get_db)):
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        return {"error": "not_configured"}
    
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return {"error": "not_authenticated"}
        
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    try:
        current = sp.current_playback()
        if not current or not current.get('item'):
            return {"is_playing": False}
            
        item = current['item']
        artist_name = ", ".join([artist['name'] for artist in item.get('artists', [])])
        
        album_art = ""
        if item.get('album') and item['album'].get('images'):
            album_art = item['album']['images'][0]['url']
            
        return {
            "is_playing": current.get('is_playing', False),
            "track_name": item.get('name', 'Desconhecido'),
            "artist_name": artist_name,
            "album_art": album_art,
            "progress_ms": current.get('progress_ms', 0),
            "duration_ms": item.get('duration_ms', 0),
            "device_name": current.get('device', {}).get('name', 'Unknown')
        }
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Erro ao buscar now-playing: {e}")
        return {"error": "api_error"}


class SpotifyControlRequest(BaseModel):
    action: str
    volume: int = None

@router.post("/control")
def control_playback(req: SpotifyControlRequest, request: Request, db: Session = Depends(get_db)):
    sp_oauth = get_spotify_oauth(db, request)
    if not sp_oauth:
        raise HTTPException(status_code=400, detail="Not configured")
        
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    
    try:
        # Pega dispositivo ativo atual
        current = sp.current_playback()
        device_id = None
        if current and current.get('device'):
            device_id = current['device']['id']
            
        if not device_id:
            # Tenta achar Alfredo Speaker
            devices = sp.devices()
            if devices and devices.get('devices'):
                for d in devices['devices']:
                    if d.get('name') == 'Alfredo Speaker':
                        device_id = d['id']
                        break
                if not device_id:
                    device_id = devices['devices'][0]['id']
                    
        if not device_id:
            raise HTTPException(status_code=404, detail="No active devices")

        if req.action == "play":
            sp.start_playback(device_id=device_id)
        elif req.action == "pause":
            sp.pause_playback(device_id=device_id)
        elif req.action == "next":
            sp.next_track(device_id=device_id)
        elif req.action == "prev":
            sp.previous_track(device_id=device_id)
        elif req.action == "volume" and req.volume is not None:
            sp.volume(req.volume, device_id=device_id)
        else:
            raise HTTPException(status_code=400, detail="Unknown action")
            
        return {"status": "success"}
    except spotipy.exceptions.SpotifyException as e:
        logger.error(f"Erro no controle do spotify: {e}")
        raise HTTPException(status_code=500, detail=str(e))
