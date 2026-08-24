from core.brain.memory.database import SessionLocal
from core.brain.memory import models
db = SessionLocal()
print("Scene device types:", set([c.device_type for c in db.query(models.SmartDevice).filter(models.SmartDevice.entity_id.like("scene.%")).all()]))
