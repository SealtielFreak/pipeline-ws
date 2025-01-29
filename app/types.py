import enum
import typing
import uuid

UUID = typing.TypeVar("UUID", str, uuid.UUID)
Token = typing.TypeVar("Token", str, bytes)


class StatusQuery(enum.StrEnum):
    SUCCESS = 'success'
    FAILURE = 'failure'
