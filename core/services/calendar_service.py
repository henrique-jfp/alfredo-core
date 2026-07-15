"""
calendar_service.py

Serviço centralizado para operações com a agenda (Event).
Toda consulta ao banco de eventos deve passar por aqui,
evitando duplicação de lógica e inconsistências de timezone.
"""

import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.brain.memory import models

logger = logging.getLogger("alfredo.calendar_service")

TZ = ZoneInfo("America/Sao_Paulo")

# --------------------------------------------------------------------------- #
# Utilitários de Timezone
# --------------------------------------------------------------------------- #

def ensure_utc(dt: datetime) -> datetime:
    """Garante que um datetime seja timezone-aware em UTC.
    Se for naive, assume que está em UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Converte um datetime (UTC ou naive) para o timezone local (America/Sao_Paulo)."""
    utc_dt = ensure_utc(dt)
    return utc_dt.astimezone(TZ)


def now_utc() -> datetime:
    """Retorna o datetime atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """Retorna o datetime atual no timezone local."""
    return datetime.now(TZ)


# --------------------------------------------------------------------------- #
# Migração legada
# --------------------------------------------------------------------------- #

def migrate_legacy_events(db: Session) -> int:
    """
    Corrige eventos legados que foram salvos com room_id='google_sync' ou
    sem source definido.
    """
    count = 0
    # Corrige eventos com room_id='google_sync' (modelo antigo)
    old_google = db.query(models.Event).filter(
        models.Event.room_id == "google_sync"
    ).all()
    for ev in old_google:
        ev.room_id = None
        ev.source = "GOOGLE"
        if ev.google_event_id is None:
            ev.google_event_id = "legacy"
        count += 1

    # Corrige eventos com google_event_id mas source=LOCAL (modelo antigo)
    old_synced = db.query(models.Event).filter(
        models.Event.google_event_id.isnot(None),
        models.Event.source == "LOCAL"
    ).all()
    for ev in old_synced:
        ev.source = "GOOGLE"
        if ev.room_id == "google_sync":
            ev.room_id = None
        count += 1

    if count > 0:
        db.commit()
        logger.info(f"Migração legada: {count} eventos corrigidos (source, room_id)")
    return count


# --------------------------------------------------------------------------- #
# Consultas centralizadas
# --------------------------------------------------------------------------- #

def get_events_for_room(
    db: Session,
    room_id: str,
    start: datetime,
    end: datetime
) -> List[models.Event]:
    """
    Retorna todos os eventos relevantes para uma sala:
    - Eventos LOCAIS com room_id == sala_atual
    - Eventos GOOGLE (globais, room_id = None)
    - Eventos de outras origens globais (room_id = None)

    Datas devem ser timezone-aware UTC.
    """
    start_utc = ensure_utc(start)
    end_utc = ensure_utc(end)

    events = db.query(models.Event).filter(
        models.Event.start_time >= start_utc,
        models.Event.start_time <= end_utc,
        or_(
            models.Event.room_id == room_id,
            models.Event.source != "LOCAL",  # GOOGLE, OUTLOOK, CALDAV etc.
        )
    ).order_by(models.Event.start_time.asc()).all()

    return events


def get_events_for_scheduler(
    db: Session,
    start: datetime,
    end: Optional[datetime] = None
) -> List[models.Event]:
    """
    Retorna eventos futuros para o scheduler (notificações).
    Inclui eventos LOCAIS e GLOBAIS.
    """
    start_utc = ensure_utc(start)
    if end is None:
        end_utc = start_utc + timedelta(days=365)
    else:
        end_utc = ensure_utc(end)

    events = db.query(models.Event).filter(
        models.Event.start_time >= start_utc,
        models.Event.start_time <= end_utc
    ).order_by(models.Event.start_time.asc()).all()

    return events


def get_upcoming_events(
    db: Session,
    room_id: str,
    limit: int = 5
) -> List[models.Event]:
    """
    Retorna os próximos eventos (LOCAIS + GLOBAIS) a partir de agora.
    """
    now = now_utc()
    events = db.query(models.Event).filter(
        models.Event.start_time >= now,
        or_(
            models.Event.room_id == room_id,
            models.Event.source != "LOCAL",
        )
    ).order_by(models.Event.start_time.asc()).limit(limit).all()
    return events


def create_event(
    db: Session,
    title: str,
    start_time: datetime,
    room_id: Optional[str] = None,
    source: str = "LOCAL",
    reminders: str = "60",
    google_event_id: Optional[str] = None,
    google_updated: Optional[str] = None,
) -> models.Event:
    """Cria um evento com tratamento de timezone."""
    start_utc = ensure_utc(start_time)

    event = models.Event(
        title=title,
        start_time=start_utc,
        room_id=room_id,
        source=source,
        reminders=reminders,
        google_event_id=google_event_id,
        google_updated=google_updated,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
