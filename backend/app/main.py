from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.domain.errors import Conflict, DomainError, Forbidden, InvalidData, NotFound

_STATUS_BY_ERROR = {NotFound: 404, Conflict: 409, Forbidden: 403, InvalidData: 422}


def _domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status = next((s for cls, s in _STATUS_BY_ERROR.items() if isinstance(exc, cls)), 400)
    return JSONResponse(status_code=status, content={"detail": exc.message, "code": exc.code})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(DomainError, _domain_error_handler)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
