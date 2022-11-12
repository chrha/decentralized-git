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
import asyncio
import websockets
import json
import sys
BUFFER_SIZE = 4096



async def message(message):
    async with websockets.connect("ws://localhost:2225") as socket:
        await socket.send(message)
        await socket.recv()


if __name__ == '__main__':
    msg = json.loads(sys.argv[1])
    print(msg)
    asyncio.get_event_loop().run_until_complete(message(json.dumps(msg)))
