import os
from core.brain.memory.database import SessionLocal
from core.brain.memory.models import Setting

def fix():
    db = SessionLocal()
    s = db.query(Setting).filter(Setting.key == 'assistant_voice').first()
    if s:
        s.value = 'pt-BR-FranciscaNeural'
        db.commit()
    db.close()

if __name__ == "__main__":
    fix()
