"""
Script de configuração do Spotify para o Alfredo.

Uso:
    python scripts/setup_spotify.py

Lê as credenciais do .env, salva no banco de dados e abre o navegador
para autorização OAuth.
"""
import os
import sys
import webbrowser
from pathlib import Path

# Garante que a pasta raiz do projeto está no path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from dotenv import load_dotenv
load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SERVER_PORT = os.getenv("PORT", "10001")

if not CLIENT_ID or not CLIENT_SECRET:
    print("=" * 60)
    print("SPOTIFY NÃO CONFIGURADO")
    print("=" * 60)
    print()
    print("1. Acesse https://developer.spotify.com/dashboard")
    print("2. Crie um App (qualquer nome)")
    print("3. Em 'EDIT SETTINGS', adicione no Redirect URIs:")
    print()
    print("   http://localhost:10001/api/spotify/callback")
    print()
    print("4. Copie o Client ID e Client Secret")
    print()
    print("5. Edite o arquivo .env e preencha:")
    print("   SPOTIFY_CLIENT_ID=seu_id")
    print("   SPOTIFY_CLIENT_SECRET=seu_secret")
    print()
    print("6. Rode este script novamente")
    print()
    sys.exit(1)

# Salva no banco de dados
from core.brain.memory.database import SessionLocal
from core.brain.memory import models
from core.services.env_manager import set_env_var

db = SessionLocal()
try:
    spotify = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "spotify"
    ).first()

    if not spotify:
        spotify = models.AppIntegration(
            app_name="spotify",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            is_connected=False
        )
        db.add(spotify)
    else:
        spotify.client_id = CLIENT_ID
        spotify.client_secret = CLIENT_SECRET
        spotify.is_connected = False

    db.commit()
    print("✓ Credenciais salvas no banco de dados")
finally:
    db.close()

# Detecta IP local
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('10.255.255.255', 1))
    local_ip = s.getsockname()[0]
except Exception:
    local_ip = "127.0.0.1"
finally:
    s.close()

redirect_uri = f"http://{local_ip}:{SERVER_PORT}/api/spotify/callback"

# Monta URL de autorização
from spotipy.oauth2 import SpotifyOAuth
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=redirect_uri,
    scope="user-modify-playback-state user-read-playback-state",
    cache_path=os.path.join(os.getcwd(), ".spotify_cache"),
    open_browser=False
)

auth_url = auth_manager.get_authorize_url()

print()
print("=" * 60)
print("AUTORIZAÇÃO SPOTIFY")
print("=" * 60)
print()
print(f"IP detectado: {local_ip}")
print(f"Redirect URI: {redirect_uri}")
print()
print("IMPORTANTE: Este Redirect URI precisa estar cadastrado no")
print("Spotify Developer Dashboard → EDIT SETTINGS → Redirect URIs")
print()
print("Abrindo navegador para autorização...")
print()

webbrowser.open(auth_url)

print("Após autorizar, você será redirecionado para uma página")
print("de sucesso. Pode fechá-la.")
print()
print("Pronto! O Spotify está configurado.")
print("Digite 'Alfredo, toque uma música' para testar.")
print()
