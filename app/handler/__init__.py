from fastapi.responses import JSONResponse

from app.schemes import MessageResponse
from app.types import StatusQuery


async def response_http_exception_handler(request, exc):
    error_response = MessageResponse(
        status=StatusQuery.FAILURE,
        details=str(exc.detail)
    )

    return JSONResponse(status_code=200, content=error_response.model_dump())


async def http_exception_handler(request, exc):
    if exc.status_code in [400, 401, 403, 404, 406, 422]:
        error_response = MessageResponse(
            status=StatusQuery.FAILURE,
            details=str(exc.detail)
        )

        return JSONResponse(status_code=200, content=error_response.model_dump())

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


async def invalid_credentials_handler(request, exc):
    error_response = MessageResponse(
        status=StatusQuery.FAILURE,
        details="Signature verification failed."
    )

    return JSONResponse(status_code=200, content=error_response.model_dump())


async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )
