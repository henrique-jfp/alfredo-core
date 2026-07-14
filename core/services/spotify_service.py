import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from typing import Optional, Dict, Any
from core.brain.memory import models

logger = logging.getLogger("alfredo.spotify_service")
CACHE_PATH = os.path.join(os.getcwd(), ".spotify_cache")

_spotify_client: Optional[spotipy.Spotify] = None
_last_creds_hash: Optional[int] = None


def _creds_hash(client_id: str, client_secret: str) -> int:
    return hash((client_id, client_secret))


def get_spotify_oauth(db, redirect_uri: str) -> Optional[SpotifyOAuth]:
    spotify = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "spotify"
    ).first()

    if not spotify or not spotify.client_id or not spotify.client_secret:
        return None

    return SpotifyOAuth(
        client_id=spotify.client_id,
        client_secret=spotify.client_secret,
        redirect_uri=redirect_uri,
        scope="user-modify-playback-state user-read-playback-state",
        cache_path=CACHE_PATH,
        open_browser=False
    )


def get_spotify_client(db, redirect_uri: Optional[str] = None) -> Optional[spotipy.Spotify]:
    global _spotify_client, _last_creds_hash

    spotify = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "spotify"
    ).first()

    if not spotify or not spotify.client_id or not spotify.client_secret:
        return None

    current_hash = _creds_hash(spotify.client_id, spotify.client_secret)
    if _spotify_client and _last_creds_hash == current_hash:
        return _spotify_client

    if not redirect_uri:
        redirect_uri = "http://127.0.0.1:10001/api/spotify/callback"

    auth_manager = get_spotify_oauth(db, redirect_uri)
    if not auth_manager:
        return None

    token_info = auth_manager.get_cached_token()
    if not token_info:
        return None

    _spotify_client = spotipy.Spotify(auth_manager=auth_manager)
    _last_creds_hash = current_hash
    return _spotify_client


def get_best_device(sp) -> Optional[str]:
    devices = sp.devices()
    logger.info(f"Spotify devices encontrados: {devices}")
    if not devices or not devices.get('devices'):
        return None

    for d in devices['devices']:
        if d.get('name') == 'Alfredo Speaker':
            logger.info(f"Usando Alfredo Speaker: {d['id']}")
            return d['id']

    for d in devices['devices']:
        if d.get('is_active'):
            logger.info(f"Usando dispositivo ativo: {d['id']}")
            return d['id']

    device = devices['devices'][0]
    logger.info(f"Usando primeiro dispositivo disponível: {device['id']}")
    return device['id']


def search_and_play(sp, query: str, device_id: str) -> Optional[Dict[str, Any]]:
    results = sp.search(q=query, limit=5, type='track,artist,playlist')

    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        try:
            sp.start_playback(
                device_id=device_id,
                context_uri=track['album']['uri'],
                offset={"uri": track['uri']}
            )
        except Exception:
            sp.start_playback(device_id=device_id, uris=[track['uri']])
        return {"type": "track", "name": track['name'], "artist": track['artists'][0]['name']}

    if results['playlists']['items']:
        playlist = results['playlists']['items'][0]
        sp.start_playback(device_id=device_id, context_uri=playlist['uri'])
        return {"type": "playlist", "name": playlist['name']}

    if results['artists']['items']:
        artist = results['artists']['items'][0]
        sp.start_playback(device_id=device_id, context_uri=artist['uri'])
        return {"type": "artist", "name": artist['name']}

    return None


def control_playback(sp, action: str, device_id: Optional[str] = None, volume: Optional[int] = None):
    kwargs = {}
    if device_id:
        kwargs["device_id"] = device_id

    if action in ("pause", "stop"):
        sp.pause_playback(**kwargs)
    elif action in ("resume", "play"):
        sp.start_playback(**kwargs)
    elif action == "next":
        sp.next_track(**kwargs)
    elif action in ("previous", "prev"):
        sp.previous_track(**kwargs)
    elif action == "volume" and volume is not None:
        sp.volume(max(0, min(100, int(volume))), **kwargs)


def get_now_playing(sp) -> Optional[Dict[str, Any]]:
    try:
        current = sp.current_playback()
        if not current or not current.get('item'):
            return {"is_playing": False}

        item = current['item']
        return {
            "is_playing": current.get('is_playing', False),
            "track_name": item.get('name', 'Desconhecido'),
            "artist_name": ", ".join(a['name'] for a in item.get('artists', [])),
            "album_art": item.get('album', {}).get('images', [{}])[0].get('url', '') if item.get('album') else '',
            "progress_ms": current.get('progress_ms', 0),
            "duration_ms": item.get('duration_ms', 0),
            "device_name": current.get('device', {}).get('name', 'Unknown')
        }
    except SpotifyException as e:
        logger.error(f"Erro ao buscar now-playing: {e}")
        return {"error": "api_error"}
