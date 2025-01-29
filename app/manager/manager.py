import asyncio
import collections
import contextlib
import typing

from starlette.websockets import WebSocket

from app.manager.pipeline import PipelineBuffer
from app.schemes import CommandPipeline

C = typing.TypeVar("C")

Trigger = typing.Callable[[PipelineBuffer], typing.Awaitable[bool]]
Task = typing.Callable[[PipelineBuffer], typing.Awaitable[None]]

async def send_model(websocket: WebSocket, model: C):
    await websocket.send_json(model.model_dump())


async def read_model(websocket: WebSocket, model_class: typing.Type[C]) -> C:
    data = await websocket.receive_json()

    return model_class(**data)


class CommandManager:
    def __init__(self, websocket: WebSocket):
        self.__websocket = websocket
        self.__handler = {}
        self.__trigger_handler = {
            "startup": self.__generate_handler("startup"),
            "finished": self.__generate_handler("finished"),
        }
        self.__event_trigger = {
            "startup": asyncio.Event()
        }

    @property
    def websocket(self):
        return self.__websocket

    def attach(self, name: str):
        async def task(func):
            await func()

        self.add(name, task)

        return task

    def __generate_handler(self, name: str, task: typing.Optional[Trigger | Task] = None):
        async def __empty_trigger(pipeline: PipelineBuffer) -> bool:
            return True

        if task is None:
            task = __empty_trigger

        _event = asyncio.Event()
        _queue = collections.deque()
        _pipe = PipelineBuffer(name, self.websocket, _queue, _event)

        return (
            task,
            _pipe,
            _queue,
            _event
        )

    def set_startup(self, task: Trigger):
        self.__trigger_handler["startup"] = self.__generate_handler("startup", task)

    def set_finished(self, task: Trigger):
        self.__trigger_handler["finished"] = self.__generate_handler("finished", task)

    def add(self, name: str, task: Task):
        async def task_events_trigger(pipeline):
            if event := self.__event_trigger.get("startup"):
                print("Waiting")
                await event.wait()
                print("Startup")

            await task(pipeline)

        self.__handler[name] = self.__generate_handler(name, task_events_trigger)

    async def schedule(self):
        all_tasks_queue = []

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

        for task_name, (task, pipe, queue, event) in self.__handler.items():
            all_tasks_queue.append(asyncio.create_task(task(pipe)))

        await asyncio.gather(*all_tasks_queue)
        await self.__schedule_triggers_manager()

    async def __execute_trigger(self, name: str):
        result = self.__trigger_handler.get(name)

        if not result:
            return False

        task, pipe, queue, event = result
        return await task(pipe)

    async def __schedule_triggers_manager(self):
        startup_status = await self.__execute_trigger("startup")

        if startup_status:
            if event := self.__event_trigger.get("startup"):
                event.set()

        await self.__execute_trigger("finished")
