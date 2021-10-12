from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import random
import json
import db
import os


port = random.randint(1000,5000)
#os.makedirs("remote",exist_ok=True )

#store all peers in server impl
#local client sends to local server that then sends to the peers, listen on two sockets maybe
peers = []
my_path = f"ws://localhost:{port}"
remote = f"{port}/remote/objects"
os.makedirs(remote,exist_ok=True)
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers
async def send_commit_to_peer(websocket, path):
    global peers
    global port
    payload = await websocket.recv()
    msg = json.loads(payload)


    if "file" in msg:
        db.append_commit(msg["file"],msg["body"],f'{remote}/dag.db')
        hash=f'{remote}/{msg["file"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(msg["body"].encode())

    if peers:
        for peer in peers:
            async with websockets.connect(peer) as socket:
                await socket.send(payload)

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    global port
    global remote
    payload = await websocket.recv()
    message = json.loads(payload)


    
    if 'peers' in message:
        peers = peers + message['peers']
        peers = list(dict.fromkeys(peers))
        try:
            peers.remove(my_path)
        except:
            pass
    elif 'file' in message:
        db.append_commit(message['file'],message['body'],f'{remote}/dag.db')
        hash=f"{remote}/{message['file']}"
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(message["body"].encode())
        await websocket.send("thx")
    
    elif "fetch" in message:
        await websocket.send("OK")
        await send_all_files(message["fetch"])

async def send_all_files(path):
    #only send commit files, not blobs or trees
    #fix pls
    keys = db.get_all_keys(f'{remote}/dag.db')
    print(keys)
    for goid in keys:
        with open(f"{remote}/{goid.decode()}", 'rb') as f:
            data= f.read().decode()
        msg=json.dumps({
            "file": goid.decode(),
            "body": data
        })
        async with websockets.connect(path) as socket:
            await socket.send(msg)
            payload = await socket.recv()


async def fetch_peers():
    global peers
    async with websockets.connect("ws://localhost:5555") as socket:
        await socket.send(my_path)
        payload = await socket.recv()
        msg = json.loads(payload)
        peers = peers + msg['peers']
        peers = list(dict.fromkeys(peers))

async def fetch_data():
    if peers:
        async with websockets.connect(peers[0]) as socket:
            await socket.send(json.dumps({"fetch":my_path}))
            payload = await socket.recv()

async def disconnect():
    async with websockets.connect("ws://localhost:5555") as socket:
        await socket.send(my_path)
        payload = await socket.recv()


if __name__ == '__main__':
    try:
        asyncio.get_event_loop().run_until_complete(fetch_peers())
        start_server1 = websockets.serve(send_commit_to_peer,'localhost',2223)
        start_server2 = websockets.serve(recive_commit_from_peer,'localhost',port)
        asyncio.get_event_loop().run_until_complete(start_server1)
        asyncio.get_event_loop().run_until_complete(start_server2)
        asyncio.get_event_loop().run_until_complete(fetch_data())
        asyncio.get_event_loop().run_forever()
    finally:
        asyncio.get_event_loop().run_until_complete(disconnect())
    
