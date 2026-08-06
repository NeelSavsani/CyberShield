import asyncio

async def main():
    loop = asyncio.get_running_loop()
    print(type(loop))

asyncio.run(main())