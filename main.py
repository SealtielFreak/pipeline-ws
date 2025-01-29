import asyncio

from fastapi import FastAPI, WebSocket, HTTPException
from jwt import InvalidSignatureError

from app.depends import DependPipelineSession
from app.handler import response_http_exception_handler, http_exception_handler, global_exception_handler, \
    invalid_credentials_handler
from app.handler.exception import ResponseException
from app.manager.pipeline import PipelineBuffer

app = FastAPI()

app.add_exception_handler(ResponseException, response_http_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(InvalidSignatureError, invalid_credentials_handler)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.websocket("/pipeline")
async def websocket(websocket: WebSocket, pipeline: DependPipelineSession):
    async def task_a(pipeline: PipelineBuffer):
        await pipeline.send(f"Hello World from A!")

        while True:
            echo = await pipeline.receive()
            await pipeline.send(f"<<A>>: {echo}")

    async def task_b(pipeline: PipelineBuffer):
        await websocket.send_text("Hello World from B!")

        while True:
            echo = await pipeline.receive()
            await pipeline.send(f"<<B>>: {echo}")

            await asyncio.sleep(3)

    async def task_c(pipeline: PipelineBuffer):
        while True:
            await pipeline.send("Hello World from C!")
            await asyncio.sleep(5)

    async with pipeline.session(websocket) as session:
        session.add("A", task_a)
        session.add("B", task_b)
        session.add("C", task_c)

        await session.schedule()
