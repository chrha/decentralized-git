"""
Copyright (C) 2022  Christian Habib & Ilian Ayoub

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
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
vote_cnt = 0

#Generate new RSA keys
pr_key=RSA.generate(2048)
pu_key=pr_key.public_key()

priv_key = pr_key.export_key()
pub_key= pu_key.export_key().decode()


os.makedirs(remote_ref,exist_ok=True)
os.makedirs(remote_obj,exist_ok=True)
#when a local client connects to this channel and sends a commit, it will be sent to the rest of the peers

def add_file(filename, body):
    hash=f'{remote_path}/{filename}'
    os.makedirs(os.path.dirname(hash),exist_ok=True )
    with open(hash, 'wb') as f:
        f.write(body.encode())


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
        body = msg['body']
        if not sec.is_valid(msg, ledger_path):
            await websocket.send("Invalid commit")
            print("NOT VALID")
            return
        if ref != "refs/heads/master":
            add_file(ref, body)
            
            add_file("bajs1", "bajs")
        
        del msg['ref']
        del msg['body']
        print(ref)
        for key in msg:
            block=db.create_block(key, msg[key], ledger_path, ref, pub_key, pr_key)
            if block:
                blocks.append(block)
                if ref != "refs/heads/master":
                    print("not master")
                    db.add_block(block, ledger_path)
                    add_file("bajs2", "bajs")
            if ref != "refs/heads/master":
                print(f"not master {ref}")
                print(ref == "refs/heads/master")
                add_file(ref, body)
                
                

    

    if peers:
        if blocks !=[]:
            message= json.loads(payload)
            print("signatures exist")
            message["blocks"] = blocks
            message["path"] = my_path
            payload=json.dumps(message)

        for peer in peers:
            async with websockets.connect(peer[0]) as socket:
                await socket.send(payload)
                print(await socket.recv())
    await websocket.send("OK")
    
        

#connected to by other peers to recive commit, and update peers
async def recive_commit_from_peer(websocket, path):
    global peers
    global port
    global remote_obj
    global vote_cnt
    payload = await websocket.recv()

    message = json.loads(payload)


    if "peers" in message:
        peer_list=message["peers"]
        unique_peers=[]
        for elem in peer_list:
            if elem not in peers:
                unique_peers.append(elem)
        peers = peers + unique_peers
        try:
            peers.remove([my_path,pub_key])
        except:
            pass
        await websocket.send("Peers received" )
        return
    elif "response" in message:
        print(message["response"])
        await websocket.send("OK response received")
        return
    elif "ref" in message:
        ref = message['ref']
        blocks = message['blocks']
        body = message['body']
        if message['path'] != my_path:
            key = get_peer_key(message['path'])
        else:
            key = pub_key       

        
        if "vote" in message:
            if message["vote"] == "y":
                vote_cnt += 1

            if vote_cnt < len(peers)*0.5:
                await websocket.send(f"Vote recived at {my_path}")
                return
            print("Consensus reached")
            async with websockets.connect(message['path']) as socket:
                await socket.send(json.dumps({"response" : f"{my_path} has made your request permanant"}))
                print(await socket.recv())
        
        if ref == "refs/heads/master" and not "vote" in message:
            await websocket.send("OK merge request recived")
            await websocket.close()
            va = input("y/n: ")
            m = json.loads(payload)
            m["vote"] = va
            p = json.dumps(m)
            for peer in peers:
                async with websockets.connect(peer[0]) as socket:
                    await socket.send(p)
                    print(await socket.recv())
            return
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

        if message["vote"]:
            del message["vote"]
        del message['ref']
        del message['body']
        for block in blocks:
            db.add_block(block, ledger_path)
        del message['blocks']
        del message['path']
        for key in message:
            add_file(key, message[key])

        await websocket.send(f"Blocks recived at {my_path}")
        if ref == "refs/heads/master":
            vote_cnt = 0
        return

    await websocket.send("Badly formated message")

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

async def fetch_peers():
    global peers
    peer_list= [my_path , pub_key] 

    msgz=json.dumps( {"peer" : peer_list} )

    async with websockets.connect("ws://localhost:5555") as socket:

        await socket.send(msgz)
        payload = await socket.recv()
        msg = json.loads(payload)
        peer_list=msg["peers"]
        peers = peers + peer_list
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
