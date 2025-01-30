import asyncio
import collections
import dataclasses
import enum
import json

from starlette.websockets import WebSocket


class TypeRequest(enum.Enum):
    JSON = enum.auto()
    STRING = enum.auto()


@dataclasses.dataclass
class PipelineRequest:
    type_request: TypeRequest
    data: dict | str


class PipelineBuffer:
    def __init__(self, name: str, websocket: WebSocket, queue: collections.deque, event: asyncio.Event):
        self.__name = name
        self.__websocket = websocket
        self.__queue = queue
        self.__event = event

    async def receive(self) -> PipelineRequest:
        await self.__event.wait()
        self.__event.clear()

        data = self.__queue.pop()

        if isinstance(data, dict):
            return PipelineRequest(
                data=data,
                type_request=TypeRequest.JSON
            )
        else:
            return PipelineRequest(
                data=data,
                type_request=TypeRequest.STRING
            )

    async def send(self, data):
        if isinstance(data, str):
            await self.__websocket.send_text(data)
        elif isinstance(data, dict):
            await self.__websocket.send_json(data)

    async def clear(self):
        self.__queue.clear()
