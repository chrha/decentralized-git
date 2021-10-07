import asyncio
import websockets
import json
import sys


async def message(message):
    async with websockets.connect("ws://localhost:2223") as socket:
        await socket.send(message)


if __name__ == '__main__':
    #msg = sys.argv[1]
    p = json.dumps({"show" : "5555555"})
    asyncio.get_event_loop().run_until_complete(message(p))