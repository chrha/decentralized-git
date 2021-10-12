import asyncio
import websockets
import json
import sys
BUFFER_SIZE = 4096



async def message(message):
    async with websockets.connect("ws://localhost:2223") as socket:
        await socket.send(message)


if __name__ == '__main__':
    msg = json.loads(sys.argv[1])
    print(msg)
    asyncio.get_event_loop().run_until_complete(message(json.dumps(msg)))
