from websockets import serve
import asyncio

def handle_request(data):
    print(data["method"])

async def echo(websocket):
    async for data in websocket:
        handle_request(json.loads(data))

async def main():
    async with serve(echo, "localhost", 3000):
        await asyncio.get_running_loop().create_future()  # run forever

asyncio.run(main())

class Server()