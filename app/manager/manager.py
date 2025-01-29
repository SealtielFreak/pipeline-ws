import asyncio
import collections
import typing

from starlette.websockets import WebSocket

from app.manager.pipeline import PipelineBuffer
from app.schemes import CommandPipeline

C = typing.TypeVar("C")


async def send_model(websocket: WebSocket, model: C):
    await websocket.send_json(model.model_dump())


async def read_model(websocket: WebSocket, model_class: typing.Type[C]) -> C:
    data = await websocket.receive_json()

    return model_class(**data)


class CommandManager:
    def __init__(self, websocket: WebSocket):
        self.__websocket = websocket
        self.__handler = {}

    @property
    def websocket(self):
        return self.__websocket

    def attach(self, name: str):
        async def task(func):
            await func()

        self.add(name, task)

        return task

    def add(self, name: str, task):
        event = asyncio.Event()
        queue = collections.deque()

        self.__handler[name] = (
            task,
            PipelineBuffer(name, self.websocket, queue, event),
            queue,
            event
        )

    async def schedule(self):
        all_tasks_queue = []

        for task_name, (task, pipe, queue, event) in self.__handler.items():
            all_tasks_queue.append(asyncio.create_task(task(pipe)))

        async def schedule_pipeline_trigger():
            while True:
                for task_name, (task, pipe, queue, event) in self.__handler.items():
                    if len(queue) > 0:
                        event.set()

                    await asyncio.sleep(0.01)

        async def schedule_pipeline_queue():
            while True:
                command_pipe = await read_model(self.__websocket, CommandPipeline)

                if results := self.__handler.get(command_pipe.command):
                    task, pipe, queue, event = results

                    queue.append(command_pipe.data)

        all_tasks_queue.append(asyncio.create_task(schedule_pipeline_queue()))
        all_tasks_queue.append(asyncio.create_task(schedule_pipeline_trigger()))

        await asyncio.gather(*all_tasks_queue)
