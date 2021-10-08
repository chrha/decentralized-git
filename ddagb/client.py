import asyncio
import websockets
import json
import sys
BUFFER_SIZE = 4096
path="/home/iliay038/Documents/dagit/gitcode/test_dir/.dagit/objects/8bfc83f62214a0583fbe4698abb6181503f48298"
async def message(message):
    async with websockets.connect("ws://localhost:2223") as socket:
        await socket.send(message)


if __name__ == '__main__':
    #msg = sys.argv[1]
    with open(path,"rb") as f:
        body=f.read().decode()
    p = json.dumps({"file" : "8bfc83f62214a0583fbe4698abb6181503f48298", "body": body })
    asyncio.get_event_loop().run_until_complete(message(p))
