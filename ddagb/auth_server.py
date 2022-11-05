from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import json
from base64 import b64encode
#store all peers in server impl
#local client sends to local server that then sends to the peers, listen on two sockets maybe
peers = []
number_of_peers = 0
async def peer_connected(websocket, path):
    global number_of_peers
    global peers
    payload = await websocket.recv()

    msg= json.loads(payload)

    new_peer_key= msg["peer"]
    await websocket.send(json.dumps({"peers" : peers}))
    if new_peer_key in peers:
        print(f'Peer {new_peer_key[0]} has disconnected')

        peers.remove(new_peer_key)
        number_of_peers -= 1
    else:
        print(f'Peer {new_peer_key[0]} has connected')

        peers.append(new_peer_key)
        number_of_peers += 1
    print("currently stored peers: ")
    print("[")
    for peer in peers:
        print(peer[0] + "  ")
    print("]")
    #send update to peers
    for peer in peers:
        if peer != new_peer_key:
            async with websockets.connect(peer[0]) as socket:
                await socket.send(json.dumps({"peers" : peers}))
                await socket.recv()

if __name__ == '__main__':

    start_server = websockets.serve(peer_connected,'localhost',5555)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
