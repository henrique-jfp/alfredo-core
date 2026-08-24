from core.services.samsung_tv import SamsungTVManager
import asyncio

async def check():
    from core.brain.memory.database import SessionLocal
    from core.brain.memory import models
    db = SessionLocal()
    config = db.query(models.TVConfig).first()
    
    tv = SamsungTVManager(
        ip=config.ip_address, 
        mac=config.mac_address, 
        smartthings_pat=config.smartthings_pat, 
        smartthings_device_id=config.smartthings_device_id
    )
    res = await tv.get_status()
    print("STATUS:", res)

asyncio.run(check())
