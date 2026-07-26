import asyncio
from core.services.samsung_tv import SamsungTVManager

async def test():
    tv = SamsungTVManager('192.168.0.36')
    print(await tv.send_key('KEY_VOLUP'))

asyncio.run(test())
