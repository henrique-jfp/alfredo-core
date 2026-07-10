import logging
import os
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session

from core.brain.memory import models
from core.brain.memory.database import get_db
from core.services.google_calendar import (
    get_authorization_url,
    exchange_code,
    sync_all,
    get_sync_status,
)

logger = logging.getLogger("alfredo.google_auth")
router = APIRouter(prefix="/api/auth/google", tags=["Google Auth"])


@router.get("/authorize")
def google_authorize():
    """Redireciona para o Google OAuth consent screen."""
    auth_url = get_authorization_url()
    return RedirectResponse(auth_url)


@router.get("/callback")
def google_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Callback do Google OAuth. Recebe o código e troca por token."""
    if not code or not state:
        return HTMLResponse("<h2>Erro: parâmetros ausentes</h2><p>Faltou code ou state.</p>", status_code=400)

    token_json = exchange_code(code, state)
    if not token_json:
        return HTMLResponse("<h2>Erro na autenticação</h2><p>Não foi possível obter o token. Tente novamente.</p>", status_code=400)

    integ = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "google_calendar"
    ).first()
    if not integ:
        integ = models.AppIntegration(
            app_name="google_calendar",
            client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
            token_data=token_json,
            is_connected=True,
        )
        db.add(integ)
    else:
        integ.client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        integ.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        integ.token_data = token_json
        integ.is_connected = True
    db.commit()

    return HTMLResponse(f"""<html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#0b0c0e;color:#e4e4e7;">
<div style="text-align:center;padding:2rem;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;background:rgba(255,255,255,0.02);">
<h1 style="color:#d4a24e;">Google Calendar Conectado!</h1>
<p style="color:#a1a1aa;">A sincronia bidirecional está ativa.</p>
<p style="color:#52525b;font-size:0.875rem;">Você já pode fechar esta aba.</p>
</div></body></html>""")


@router.get("/status")
def google_status(db: Session = Depends(get_db)):
    """Status da integração com Google Calendar."""
    return get_sync_status(db)


@router.post("/sync")
def google_sync(db: Session = Depends(get_db)):
    """Dispara sincronia manual bidirecional."""
    result = sync_all(db)
    return {"status": "success", "result": result}
