import typing

from pydantic import BaseModel, Field

from app.types import StatusQuery, Token

H = typing.TypeVar("H")


class AccessCredentials(BaseModel):
    token: Token = Field(..., alias="token")


class CommandPipeline(BaseModel, typing.Generic[H]):
    data: H | typing.List[H] = Field(..., alias="data")
    command: str = Field(..., alias="command")


class DataResponse(BaseModel, typing.Generic[H]):
    data: H | typing.List[H] = Field(..., alias="data")
    status: StatusQuery = Field(..., alias="status")


class MessageResponse(BaseModel):
    details: str = Field(..., alias="details")
    status: StatusQuery = Field(..., alias="status")
