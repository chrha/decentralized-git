import asyncio
import websockets
import json
async def message():
    async with websockets.connect("ws://localhost:2223") as socket:
        msg = input("What :")
        await socket.send(json.dumps({ 'message' : msg}))


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(message())