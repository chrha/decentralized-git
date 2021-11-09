from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import random
import json
import db
import os
import sec


port = random.randint(1000,5000)
peers = []
my_path = f"ws://localhost:{port}"
remote_path = f"{port}/remote/.dagit"
remote_obj = f"{remote_path}/objects"
remote_ref = f"{remote_path}/refs/heads"
ledger_path = f"{port}/dag.db"

os.makedirs(remote_ref,exist_ok=True)
os.makedirs(remote_obj,exist_ok=True)
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers
async def send_commit_to_peer(websocket, path):
    global peers
    global port
    payload = await websocket.recv()
    msg = json.loads(payload)

    if "ref" in msg:
        sec.is_valid(msg)

        hash=f'{remote_path}/{msg["ref"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(msg["body"].encode())
        del msg['ref']
        del msg['body']
        for key in msg:
            try:
                db.append_commit(key, msg[key], ledger_path)
            except:
                print(key)
                return
            hash=f'{remote_obj}/{key}'
            os.makedirs(os.path.dirname(hash),exist_ok=True )
            with open(hash, 'wb') as f:
                f.write(msg[key].encode())
    
    if peers:
        for peer in peers:
            async with websockets.connect(peer) as socket:
                await socket.send(payload)
                await socket.recv()

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    global port
    global remote_obj
    payload = await websocket.recv()
    message = json.loads(payload)


    
    if 'peers' in message:
        peers = peers + message['peers']
        peers = list(dict.fromkeys(peers))
        try:
            peers.remove(my_path)
        except:
            pass
    
    elif "ref" in message:
        sec.is_valid(message)
        hash=f'{remote_path}/{message["ref"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(message["body"].encode())
        del message['ref']
        del message['body']
        for key in message:
            print(2)
            try:
                db.append_commit(key, message[key], ledger_path)
            except:
                print(key)
                return
            hash=f'{remote_obj}/{key}'
            os.makedirs(os.path.dirname(hash),exist_ok=True )
            with open(hash, 'wb') as f:
                f.write(message[key].encode())
        
        await websocket.send("thx")
    
    elif "fetch" in message:
        await websocket.send("OK")
        await send_all_files(message["fetch"])

async def send_all_files(path):

    onlyfiles = [f for f in os.listdir(remote_obj) if os.path.isfile(os.path.join(remote_obj, f))]
    for goid in onlyfiles:
        with open(f"{remote_obj}/{goid}", 'rb') as f:
            data= f.read().decode()
        msg=json.dumps({
            "file": goid,
            "body": data
        })
        async with websockets.connect(path) as socket:
            await socket.send(msg)
            payload = await socket.recv()
    refs = [f for f in os.listdir(f'{remote_path}/refs/heads') if os.path.isfile(os.path.join(f'{remote_path}/refs/heads', f))]
    for ref in refs:
        with open(f'{remote_path}/refs/heads/{ref}', 'rb') as f:
            data= f.read().decode()
        msg=json.dumps({
            "ref": f'/refs/heads/{ref}',
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
    
