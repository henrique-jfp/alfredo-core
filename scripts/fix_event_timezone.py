"""Corrige eventos criados com timezone errado via dashboard.

Antes da correção (Jul/2026), o POST /api/dashboard/events
assumia que datetime sem timezone era UTC, quando na verdade
estava no fuso America/Sao_Paulo (BRT = UTC-3).

Isso fazia eventos serem armazenados 3h a menos que o correto.

Ex: usuário selecionou 14:00 BRT → armazenado como 14:00 UTC
    (deveria ser 17:00 UTC). Ao exibir: 11:00 BRT.

Uso:
    cd C:\Projetos Pessoais\alfredo-core
    python scripts/fix_event_timezone.py --dry-run   # só mostra
    python scripts/fix_event_timezone.py --apply      # aplica
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo
from core.brain.memory.database import SessionLocal
from core.brain.memory import models

TZ = ZoneInfo("America/Sao_Paulo")
DRY_RUN = "--dry-run" in sys.argv
APPLY = "--apply" in sys.argv

if not DRY_RUN and not APPLY:
    print("Use --dry-run para simular ou --apply para aplicar.")
    sys.exit(1)

db = SessionLocal()
try:
    events = db.query(models.Event).all()
    fixed = 0
    skipped = 0

    for e in events:
        # Eventos com google_event_id foram criados por voz ou Google,
        # que SEMPRE usaram o timezone correto.
        if e.google_event_id:
            skipped += 1
            continue

        utc_dt = e.start_time
        local_dt = utc_dt.astimezone(TZ)
        diff_h = utc_dt.hour - local_dt.hour

        # Evento com google_event_id=None pode ser:
        # 1. Dashboard (antes da correção) → UTC hour ≈ BRT hour (bug)
        # 2. Dashboard (depois da correção) → UTC hour = BRT hour + 3
        # 3. Voz sem Google Calendar config. → UTC hour = BRT hour + 3
        #
        # Só corrigimos se UTC hour == BRT hour (caso 1).
        if utc_dt.hour == local_dt.hour:
            new_utc = utc_dt + timedelta(hours=3)
            new_local = new_utc.astimezone(TZ)
            if DRY_RUN:
                print(f"  #{e.id} '{e.title}': {utc_dt.strftime('%H:%M')} UTC → {local_dt.strftime('%H:%M')} BRT "
                      f"(corrigido: {new_utc.strftime('%H:%M')} UTC → {new_local.strftime('%H:%M')} BRT)")
            elif APPLY:
                e.start_time = new_utc
                db.commit()
                print(f"  ✓ #{e.id} '{e.title}': {utc_dt.strftime('%H:%M')} UTC → {new_utc.strftime('%H:%M')} UTC")
            fixed += 1
        else:
            skipped += 1

    print(f"\nResumo: {fixed} corrigidos, {skipped} ignorados.")
finally:
    db.close()
