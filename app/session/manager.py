import asyncio
import collections
import enum
import typing

from starlette.websockets import WebSocket

from app.session.pipeline import PipelineBuffer
from app.schemes import CommandPipeline

C = typing.TypeVar("C")


class TriggerStatus(enum.Enum):
    FINISHED = enum.auto()
    FAILURE = enum.auto()


TriggerStatus = bool | None | TriggerStatus
Trigger = typing.Callable[[PipelineBuffer], typing.Awaitable[TriggerStatus]]


async def send_model(websocket: WebSocket, model: C):
    await websocket.send_json(model.model_dump())


async def read_model(websocket: WebSocket, model_class: typing.Type[C]) -> C:
    data = await websocket.receive_json()

    return model_class(**data)


class TriggerTask:
    def __init__(self, name: str, websocket: WebSocket, trigger: Trigger):
        self.__handler_name = name
        self.__trigger = trigger
        self.__finished = False

        self.event = asyncio.Event()
        self.queue = collections.deque()
        self.__pipe = PipelineBuffer(name, websocket, self.queue, self.event)

    @property
    def handler_name(self):
        return str(self.__handler_name)

    @property
    def is_finished(self):
        return self.__finished

    async def __call__(self, *args, **kwargs):
        status = await self.__trigger(self.__pipe)

        return status

    def attach(self, trigger: Trigger):
        self.__trigger = trigger

    def finished(self):
        self.__finished = True


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

    def add(self, name: str, task: Trigger):
        self.__handler[name] = TriggerTask(name, self.__websocket, task)

    async def schedule(self):
        all_tasks = []

        async def schedule_pipeline_trigger():
            while True:
                for name, trigger in self.__handler.items():
                    if len(trigger.queue) > 0:
                        trigger.event.set()

                    await asyncio.sleep(0.01)

        async def schedule_pipeline_queue_task():
            while True:
                command_pipe = await read_model(self.__websocket, CommandPipeline)

                if trigger := self.__handler.get(command_pipe.command):
                    trigger.queue.append(command_pipe.data)

        for task_name, trigger in self.__handler.items():
            all_tasks.append(asyncio.create_task(trigger()))

        all_tasks.append(asyncio.create_task(schedule_pipeline_trigger()))
        all_tasks.append(asyncio.create_task(schedule_pipeline_queue_task()))

        await asyncio.gather(*all_tasks)
