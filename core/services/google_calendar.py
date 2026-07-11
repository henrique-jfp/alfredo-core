import json
import logging
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Any

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from core.brain.memory import models
from core.brain.memory.database import SessionLocal

logger = logging.getLogger("alfredo.google_calendar")
TZ = ZoneInfo("America/Sao_Paulo")

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRETS = {}
CLIENT_SECRETS["web"] = {
    "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
}


def _save_oauth_state(state: str) -> None:
    """Persiste o state OAuth no banco (tabela settings) para sobreviver a restarts."""
    db = SessionLocal()
    try:
        setting = db.query(models.Setting).filter(models.Setting.key == f"oauth_state_{state}").first()
        if not setting:
            setting = models.Setting(key=f"oauth_state_{state}", value=datetime.now(timezone.utc).isoformat())
            db.add(setting)
        else:
            setting.value = datetime.now(timezone.utc).isoformat()
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao salvar OAuth state: {e}")
        db.rollback()
    finally:
        db.close()


def _pop_oauth_state(state: str) -> bool:
    """Remove e valida o state OAuth do banco. Retorna True se existia."""
    db = SessionLocal()
    try:
        setting = db.query(models.Setting).filter(models.Setting.key == f"oauth_state_{state}").first()
        if setting:
            db.delete(setting)
            db.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao validar OAuth state: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def get_redirect_uri() -> str:
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if public_url:
        return f"{public_url}/api/auth/google/callback"
    return "http://localhost:10001/api/auth/google/callback"
def get_authorization_url() -> str:
    flow = Flow.from_client_config(CLIENT_SECRETS, scopes=SCOPES,
                                   redirect_uri=get_redirect_uri())
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    _save_oauth_state(state)
    return auth_url


def exchange_code(code: str, state: str) -> Optional[str]:
    if not _pop_oauth_state(state):
        logger.error("State inválido ou expirado no OAuth")
        return None

    flow = Flow.from_client_config(CLIENT_SECRETS, scopes=SCOPES,
                                   redirect_uri=get_redirect_uri())
    try:
        flow.fetch_token(code=code)
        return flow.credentials.to_json()
    except Exception as e:
        logger.error(f"Erro ao trocar código por token: {e}")
        return None

def get_credentials(db: Session) -> Optional[Credentials]:
    integ = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "google_calendar"
    ).first()
    if not integ or not integ.token_data:
        return None
    try:
        creds = Credentials.from_json(integ.token_data)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
            integ.token_data = creds.to_json()
            db.commit()
        return creds
    except Exception as e:
        logger.error(f"Erro ao carregar credenciais Google: {e}")
        return None

def get_calendar_service(credentials: Credentials):
    return build("calendar", "v3", credentials=credentials)

def push_event(db: Session, event: models.Event) -> bool:
    creds = get_credentials(db)
    if not creds:
        logger.warning("Sem credenciais Google para push")
        return False
    try:
        service = get_calendar_service(creds)
        local_dt = event.start_time.astimezone(TZ)
        body = {
            "summary": event.title,
            "start": {
                "dateTime": local_dt.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": (local_dt + timedelta(hours=1)).isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
        }
        if event.reminders:
            mins = [int(r.strip()) for r in event.reminders.split(",") if r.strip().isdigit()]
            if mins:
                body["reminders"] = {
                    "useDefault": False,
                    "overrides": [{"method": "popup", "minutes": m} for m in mins]
                }

        created = service.events().insert(calendarId="primary", body=body).execute()
        event.google_event_id = created.get("id")
        event.google_updated = created.get("updated")
        db.commit()
        logger.info(f"Evento '{event.title}' sincronizado para o Google Calendar (id={created.get('id')})")
        return True
    except Exception as e:
        logger.error(f"Erro no push do evento '{event.title}': {e}")
        return False

def push_pending_events(db: Session, room_id: Optional[str] = None) -> int:
    query = db.query(models.Event).filter(models.Event.google_event_id.is_(None))
    if room_id:
        query = query.filter(models.Event.room_id == room_id)
    pending = query.all()
    count = 0
    for ev in pending:
        if push_event(db, ev):
            count += 1
    return count

def pull_events(db: Session) -> int:
    creds = get_credentials(db)
    if not creds:
        return 0
    try:
        service = get_calendar_service(creds)
        now_utc = datetime.now(timezone.utc)
        time_min = (now_utc - timedelta(days=30)).isoformat() + "Z"
        time_max = (now_utc + timedelta(days=90)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        items = events_result.get("items", [])
        count = 0
        for item in items:
            gevent_id = item.get("id")
            if not gevent_id:
                continue

            existing = db.query(models.Event).filter(
                models.Event.google_event_id == gevent_id
            ).first()

            start_str = item["start"].get("dateTime", item["start"].get("date"))
            try:
                start_dt = datetime.fromisoformat(start_str)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=TZ)
                start_dt = start_dt.astimezone(timezone.utc)
            except Exception:
                continue

            title = item.get("summary", "(sem título)")

            if existing:
                g_updated = item.get("updated", "")
                if g_updated and g_updated != existing.google_updated:
                    existing.title = title
                    existing.start_time = start_dt
                    existing.google_updated = g_updated
                    db.commit()
                    count += 1
            else:
                new_event = models.Event(
                    title=title,
                    start_time=start_dt,
                    room_id="google_sync",
                    google_event_id=gevent_id,
                    google_updated=item.get("updated", ""),
                )
                db.add(new_event)
                db.commit()
                count += 1

        logger.info(f"Pull do Google Calendar: {count} eventos processados")
        return count
    except Exception as e:
        logger.error(f"Erro no pull do Google Calendar: {e}")
        return 0

def sync_all(db: Session, room_id: Optional[str] = None) -> dict:
    pushed = push_pending_events(db, room_id)
    pulled = pull_events(db)
    return {"pushed": pushed, "pulled": pulled}

def get_sync_status(db: Session) -> dict:
    total = db.query(models.Event).count()
    synced = db.query(models.Event).filter(
        models.Event.google_event_id.isnot(None)
    ).count()
    pending = total - synced
    integ = db.query(models.AppIntegration).filter(
        models.AppIntegration.app_name == "google_calendar"
    ).first()
    is_connected = bool(integ and integ.is_connected and integ.token_data)
    return {
        "is_connected": is_connected,
        "total_events": total,
        "synced_events": synced,
        "pending_events": pending,
    }
