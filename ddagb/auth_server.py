from asyncio.events import get_event_loop
from asyncio.streams import start_server
import websockets
import asyncio
import json

#store all peers in server impl
#local client sends to local server that then sends to the peers, listen on two sockets maybe
peers = []
number_of_peers = 0
async def peer_connected(websocket, path):
    global number_of_peers
    new_peer = await websocket.recv()
    await websocket.send(json.dumps({'peers' : peers}))
    if new_peer in peers:
        print(f'Peer {new_peer} has disconnected')
        peers.remove(new_peer)
        number_of_peers -= 1
    else:
        print(f'Peer {new_peer} has connected')
        peers.append(new_peer)
        number_of_peers += 1

    #send update to peers
    for peer in peers:
        if peer != new_peer:
            async with websockets.connect(peer) as socket:
                await socket.send(json.dumps({'peers' : peers}))

if __name__ == '__main__':

    start_server = websockets.serve(peer_connected,'localhost',5555)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

