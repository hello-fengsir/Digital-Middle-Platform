from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import admin, public


_SAFE_VALIDATION_ERROR_FIELDS = ("type", "loc", "msg", "ctx")


def _redact_validation_errors(
    errors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Keep validation metadata while dropping echoed request data and documentation URLs."""
    return [
        {field: error[field] for field in _SAFE_VALIDATION_ERROR_FIELDS if field in error}
        for error in errors
    ]


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=422,
        content={"detail": _redact_validation_errors(exc.errors())},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="天枢 TenSpur API", description="硬件产品资料与选型平台")
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(public.router)
    app.include_router(admin.router)
    return app


app = create_app()
