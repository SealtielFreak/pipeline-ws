import contextlib
import typing
from functools import lru_cache

from starlette.exceptions import HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.handler.exception import ResponseException
from app.manager.manager import CommandManager
from app.schemes import MessageResponse
from app.types import StatusQuery

C = typing.TypeVar("C")


class PipelineSession:
    def __init__(self):
        pass

    @contextlib.asynccontextmanager
    async def session(self, websocket: WebSocket):
        await websocket.accept()

        message = None

        try:
            try:
                yield CommandManager(websocket)
            except HTTPException as e:
                message = MessageResponse(
                    details=e.detail,
                    status=StatusQuery.FAILURE
                )
            except ResponseException as e:
                message = MessageResponse(
                    details=e.detail,
                    status=StatusQuery.FAILURE
                )
            except Exception as e:
                message = MessageResponse(
                    details="Maybe something went wrong.",
                    status=StatusQuery.FAILURE
                )

                raise e

        except WebSocketDisconnect:
            await websocket.close()
        else:
            try:
                if message is not None:
                    await websocket.send_json(message.model_dump())
            except RuntimeError:
                pass


@lru_cache
def get_pipeline_session():
    return PipelineSession()
