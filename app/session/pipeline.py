import asyncio
import collections

from starlette.websockets import WebSocket


class PipelineBuffer:
    def __init__(self, name: str, websocket: WebSocket, queue: collections.deque, event: asyncio.Event):
        self.__name = name
        self.__websocket = websocket
        self.__queue = queue
        self.__event = event

    async def receive(self):
        await self.__event.wait()
        self.__event.clear()

        return self.__queue.pop()

    async def send(self, data):
        await self.__websocket.send_text(data)
