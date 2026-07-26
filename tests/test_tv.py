import logging
logging.basicConfig(level=logging.DEBUG)
from core.services.samsung_tv import SamsungTVManager
import asyncio

async def main():
    tv = SamsungTVManager(ip="192.168.0.36")
    print("Enviando KEY_NETFLIX...")
    await tv.send_key("KEY_NETFLIX")
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
