from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import random
import json
port = random.randint(1000,5000)
#store all peers in server impl
#local client sends to local server that then sends to the peers, listen on two sockets maybe
peers = []
my_path = f"ws://localhost:{port}"
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers
async def send_commit_to_peer(websocket, path):
    message = await websocket.recv()
    for peer in peers:
        async with websockets.connect(peer) as socket:
            await socket.send(message)

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    m = await websocket.recv()
    message = json.loads(m)
    if 'message' in message:
        print(message['message'])
    elif 'peers' in message:
        peers = message['peers']
        peers.remove(my_path)



async def fetch_peers():
    global peers
    async with websockets.connect("ws://localhost:5555") as socket:
        await socket.send(my_path)
        peers = await socket.recv()



if __name__ == '__main__':

    asyncio.get_event_loop().run_until_complete(fetch_peers())
    start_server1 = websockets.serve(send_commit_to_peer,'localhost',2223)
    start_server2 = websockets.serve(recive_commit_from_peer,'localhost',port)
    asyncio.get_event_loop().run_until_complete(start_server1)
    asyncio.get_event_loop().run_until_complete(start_server2)
    asyncio.get_event_loop().run_forever()

