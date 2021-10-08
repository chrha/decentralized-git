from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import random
import json
import db
import os
port = random.randint(1000,5000)
os.makedirs("objects", exist_ok=True)
#store all peers in server impl
#local client sends to local server that then sends to the peers, listen on two sockets maybe
peers = []
my_path = f"ws://localhost:{port}"
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers
async def send_commit_to_peer(websocket, path):
    global peers
    global port
    payload = await websocket.recv()
    msg = json.loads(payload)

    if "commit" in msg:
        os.mkdir(f"../{port}")
        db.put_db(msg["commit"].encode(), payload.encode(), f"../{port}/ledger.db".encode())
    elif 'show' in msg:
        print(db.get_db(msg["show"].encode(), f"../{port}/ledger.db".encode()))
    elif 'file' in msg:
        print(msg['file']+" : " + msg['body'])
        hash=f'objects/{msg["file"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(msg['body'].encode())
    if peers:
        for peer in peers:
            async with websockets.connect(peer) as socket:
                await socket.send(payload)

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    global port
    payload = await websocket.recv()
    message = json.loads(payload)


    if 'show' in message:
        print(db.get_db(message["show"].encode(), f"../{port}/ledger.db".encode()))
    elif 'peers' in message:
        peers = peers + message['peers']
        peers = list(dict.fromkeys(peers))
        try:
            peers.remove(my_path)
        except:
            pass
    elif 'commit' in message:
        os.mkdir(f"../{port}")
        db.put_db(message["commit"].encode(), payload.encode(), f"../{port}/ledger.db".encode())

    elif 'file' in message:
        print(message['file']+" : " + message['body'])
        hash=f'objects/{message["file"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(message['body'].encode())


async def fetch_peers():
    global peers
    async with websockets.connect("ws://localhost:5555") as socket:
        await socket.send(my_path)
        payload = await socket.recv()
        msg = json.loads(payload)
        peers = peers + msg['peers']
        peers = list(dict.fromkeys(peers))



if __name__ == '__main__':

    asyncio.get_event_loop().run_until_complete(fetch_peers())
    #start_server1 = websockets.serve(send_commit_to_peer,'localhost',2223)
    start_server2 = websockets.serve(recive_commit_from_peer,'localhost',port)
    #asyncio.get_event_loop().run_until_complete(start_server1)
    asyncio.get_event_loop().run_until_complete(start_server2)
    asyncio.get_event_loop().run_forever()
