"""
Script de seed inicial da tabela `rooms`.

Popula os cômodos que já existem como referência no código do Alfredo OS.
Executar depois de reiniciar o servidor (para criar a tabela automaticamente via
Base.metadata.create_all).

Uso:
    python scripts/seed_rooms.py

Ou importe seed_rooms() no startup_event do FastAPI se preferir execução automática.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.brain.memory.database import SessionLocal
from core.brain.memory import models


ROOMS_TO_SEED = [
    {"room_id": "ROOM_LIVING", "name": "Sala"},
    {"room_id": "ROOM_OFFICE", "name": "Escritório"},
]


def seed_rooms():
    db = SessionLocal()
    try:
        created = 0
        for r in ROOMS_TO_SEED:
            existing = db.query(models.Room).filter(
                models.Room.room_id == r["room_id"]
            ).first()
            if not existing:
                db.add(models.Room(room_id=r["room_id"], name=r["name"]))
                created += 1
                print(f"  ✅ Criado cômodo: {r['room_id']} → {r['name']}")
            else:
                print(f"  ⏭️  Já existe: {r['room_id']} → {r['name']}")
        if created:
            db.commit()
            print(f"\n✔ {created} cômodo(s) criado(s) com sucesso.")
        else:
            print("\n✔ Nenhum cômodo novo para criar.")
    except Exception as e:
        db.rollback()
        print(f"Erro ao popular cômodos: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=== Seed de Cômodos ===")
    seed_rooms()
