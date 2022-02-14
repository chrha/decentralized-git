from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import random
import json
import db
import os
import sec
import hashlib
import binascii
from Crypto.PublicKey import RSA
from base64 import b64encode
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import copy

port = random.randint(1000,5000)
peers = []
my_path = f"ws://localhost:{port}"
remote_path = f"{port}/remote/.dagit"
remote_obj = f"{remote_path}/objects"
remote_ref = f"{remote_path}/refs/heads"
ledger_path = f"{port}/dag.db"

#Generate new RSA keys
pr_key=RSA.generate(2048)
pu_key=pr_key.public_key()

priv_key = pr_key.export_key()
pub_key= pu_key.export_key().decode()


os.makedirs(remote_ref,exist_ok=True)
os.makedirs(remote_obj,exist_ok=True)
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers
async def send_commit_to_peer(websocket, path):
    global peers
    global port
    sig_list=[]
    payload = await websocket.recv()
    msg = json.loads(payload)
    blocks=[]

    #message is a commit 
    if "ref" in msg:
        ref = msg['ref']
        if not sec.is_valid(msg, ledger_path):
            await websocket.send("Invalid commit")
            print("NOT VALID")
            return
        

        hash=f'{remote_path}/{msg["ref"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(msg["body"].encode())
        
        del msg['ref']
        del msg['body']
        for key in msg:
            
            print(key)
            block=db.append_commit(key, msg[key], ledger_path, ref, pub_key, pr_key)
            if block:
                blocks.append(block)
                
                #print(key + " Was not successfully added to db")
                #return
            hash=f'{remote_obj}/{key}'
            os.makedirs(os.path.dirname(hash),exist_ok=True )
            with open(hash, 'wb') as f:
                f.write(msg[key].encode())

    if peers:
        if blocks !=[]:
            message= json.loads(payload)
            print("signatures exist")
            message["blocks"] = blocks
            message["path"] = my_path
            #message["from"] = my_path
            payload=json.dumps(message)

        for peer in peers:
            async with websockets.connect(peer[0]) as socket:
                await socket.send(payload)
                print(await socket.recv())

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    global port
    global remote_obj
    payload = await websocket.recv()

    message = json.loads(payload)



    if "peers" in message:
        #peers = peers + message['peers']
        peer_list=message["peers"]
        unique_peers=[]
        for elem in peer_list:
            if elem not in peers:
                unique_peers.append(elem)
        #peer_list= list(dict.fromkeys(peer_list))
        peers = peers + unique_peers
        print("received peers: ")
        #peers = list(dict.fromkeys(peers))
        try:
            peers.remove([my_path,pub_key])
        except:
            pass
        await websocket.send("peers recived" )
        return

    elif "ref" in message:
        ref = message['ref']
        blocks = message['blocks']
        body = message['body']
        key = get_peer_key(message['path'])
        if not sec.is_signed(message, key):
            await websocket.send("Invalid sign")
            return 
        if not sec.is_valid(message, ledger_path):
            await websocket.send("Invalid commit")
            return
        if not sec.is_owner(message, key, ledger_path):
            await websocket.send("Invalid commit")
            return

        hash=f'{remote_path}/{message["ref"]}'
        os.makedirs(os.path.dirname(hash),exist_ok=True )
        with open(hash, 'wb') as f:
            f.write(message["body"].encode())
        del message['ref']
        del message['body']
        for block in blocks:
            db.add_block(block, ledger_path)
        del message['blocks']
        del message['path']
        for key in message:
            hash=f'{remote_obj}/{key}'
            os.makedirs(os.path.dirname(hash),exist_ok=True )
            with open(hash, 'wb') as f:
                f.write(message[key].encode())

        await websocket.send("Blocks recived")
        return



        
    #fixa fetch
    #elif "fetch" in message:
        #print("fff")
        #await websocket.send("sdfsdfdsf")
        #await send_all_files(message["fetch"])
    await websocket.send("badly formated message")
# Oatch for sending all files in one json
# Right now, adding a new peer after a push, it will not get all file data

def get_peer_key(path):
    for peer in peers:
        if path == peer[0]:
            return peer[1]
    return ''
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


#denna skickar t auth som i sin tur sparar path och kallar på de andras
# receive commit from peer......ta det med chris imorgon

async def fetch_peers():
    global peers
    #key=b64encode(pub_key).decode('utf-8')
    peer_list= [my_path , pub_key] #b64encode((my_path,pub_key)).decode('utf-8')

    msgz=json.dumps( {"peer" : peer_list} )
    #print("gonna get the peers to my path: " + my_path)
    #print("sending: " + msgz)

    async with websockets.connect("ws://localhost:5555") as socket:

        await socket.send(msgz)
        #print("sent message to retrieve")
        payload = await socket.recv()
        #print("awaiting peers to be retrieved")
        msg = json.loads(payload)
        peer_list=msg["peers"]
        peers = peers + peer_list
        #print(peers)
        #peers = list(dict.fromkeys(peers))
    #print("have currently these peers stored: "+peers)
async def fetch_data():
    if peers:
        async with websockets.connect(peers[0][0]) as socket:
            await socket.send(json.dumps({"fetch":my_path}))
            payload = await socket.recv()

async def disconnect():
    peer_l= [my_path , pub_key]

    msgz=json.dumps( {"peer" : peer_l} )
    print(my_path)
    async with websockets.connect("ws://localhost:5555") as socket:
        await socket.send(msgz)
        payload = await socket.recv()


if __name__ == '__main__':
    try:
        asyncio.get_event_loop().run_until_complete(fetch_peers())
        start_server1 = websockets.serve(send_commit_to_peer,'localhost',2226)
        start_server2 = websockets.serve(recive_commit_from_peer,'localhost',port)
        asyncio.get_event_loop().run_until_complete(start_server1)
        asyncio.get_event_loop().run_until_complete(start_server2)
        #asyncio.get_event_loop().run_until_complete(fetch_data())
        asyncio.get_event_loop().run_forever()
    finally:
        asyncio.get_event_loop().run_until_complete(disconnect())
