import os
import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from spotipy.exceptions import SpotifyException
from core.brain.memory import models
from core.brain.memory.database import get_db
from core.services import spotify_service

router = APIRouter(prefix="/api/spotify", tags=["spotify"])
logger = logging.getLogger("alfredo.spotify")


def _get_dynamic_redirect_uri(db: Session, request: Request) -> str | None:
    spotify_oauth = spotify_service.get_spotify_oauth(db, "http://localhost")
    if not spotify_oauth:
        return None
    base_url = str(request.base_url).rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto == "https" and base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
    return f"{base_url}/api/spotify/callback"


def _get_spotify_oauth_for_request(db: Session, request: Request):
    redirect_uri = _get_dynamic_redirect_uri(db, request)
    if not redirect_uri:
        return None
    return spotify_service.get_spotify_oauth(db, redirect_uri)


@router.get("/login")
def login(request: Request, db: Session = Depends(get_db)):
    sp_oauth = _get_spotify_oauth_for_request(db, request)
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

    sp_oauth = _get_spotify_oauth_for_request(db, request)
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
    redirect_uri = _get_dynamic_redirect_uri(db, request)
    sp = spotify_service.get_spotify_client(db, redirect_uri)
    if not sp:
        oauth = spotify_service.get_spotify_oauth(db, redirect_uri or "http://localhost")
        if not oauth:
            return {"error": "not_configured"}
        return {"error": "not_authenticated"}
    return spotify_service.get_now_playing(sp)


@router.get("/now-playing/stream")
async def stream_now_playing(request: Request, db: Session = Depends(get_db)):
    redirect_uri = _get_dynamic_redirect_uri(db, request)

    async def event_stream():
        while True:
            try:
                if await request.is_disconnected():
                    break
                sp = spotify_service.get_spotify_client(db, redirect_uri)
                if sp:
                    data = spotify_service.get_now_playing(sp)
                else:
                    data = {"error": "not_authenticated"}
                yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                logger.error(f"Erro no SSE now-playing: {e}")
                yield f"data: {json.dumps({'error': 'api_error'})}\n\n"
            await asyncio.sleep(2)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


class SpotifyControlRequest(BaseModel):
    action: str
    volume: int = None


@router.post("/control")
def control_playback(req: SpotifyControlRequest, request: Request, db: Session = Depends(get_db)):
    redirect_uri = _get_dynamic_redirect_uri(db, request)
    sp = spotify_service.get_spotify_client(db, redirect_uri)
    if not sp:
        oauth = spotify_service.get_spotify_oauth(db, redirect_uri or "http://localhost")
        if not oauth:
            raise HTTPException(status_code=400, detail="Not configured")
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        device_id = spotify_service.get_best_device(sp)
        if not device_id:
            raise HTTPException(status_code=404, detail="No active devices")

        spotify_service.control_playback(sp, req.action, device_id, req.volume)
        return {"status": "success"}
    except SpotifyException as e:
        logger.error(f"Erro no controle do spotify: {e}")
        raise HTTPException(status_code=500, detail=str(e))
