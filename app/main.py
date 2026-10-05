from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings
from app.database import Database
from app.errors import AppError, error_response
from app.logging import configure, event, request_id
from app.routes import FRONTEND_DIST, router
from app.services.ai import OpenAIAdapter


def create_app(settings: Settings | None = None, ai=None):
    settings = settings or Settings()
    configure()
    db = Database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        await db.create_tables()
        yield

    app = FastAPI(title="B7-1 AI Chat", lifespan=lifespan)
    app.state.db = db
    app.state.ai = ai or OpenAIAdapter(settings)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id.set(uuid4().hex)
        event("request_received", method=request.method, path=request.url.path)
        try:
            return await call_next(request)
        except Exception:
            event("request_failed", code="INTERNAL_ERROR")
            return error_response(AppError("INTERNAL_ERROR"))

    @app.exception_handler(AppError)
    async def application_error(request: Request, exc: AppError):
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error_response(AppError("VALIDATION_ERROR"))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        return error_response(AppError("DB_UNAVAILABLE"))

    app.include_router(router)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")
    return app
