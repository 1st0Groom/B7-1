import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from app.config import Settings
from app.database import Database
from app.errors import AppError, error_response
from app.logging import configure, event
from app.middleware import RateLimiter, RequestMiddleware
from app.routers import register_routes
from app.routers.pages import FRONTEND_DIST
from app.schemas import ErrorOutput
from app.services.ai import OpenAIAdapter
from app.services.chat import recover_pending


def create_app(settings=None, ai=None):
    settings = settings or Settings()
    configure(settings.log_level)
    db = Database(settings.database_url)

    async def recovery_loop():
        while True:
            await asyncio.sleep(15)
            try:
                await recover_pending(db)
            except SQLAlchemyError:
                event("db_save_failed", phase="recovery")

    @asynccontextmanager
    async def lifespan(app):
        try:
            app.state.ai = ai or OpenAIAdapter(settings)
            await recover_pending(db, all_pending=True)
            task = asyncio.create_task(recovery_loop())
            try:
                yield
            finally:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        finally:
            if getattr(app.state, "ai", None) is not None:
                await app.state.ai.close()
            await db.engine.dispose()

    app = FastAPI(
        title="B7-1 Learning Chat",
        lifespan=lifespan,
        docs_url=None,
        responses={
            status: {"model": ErrorOutput}
            for status in (400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 502, 503, 504)
        },
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.db = db
    app.state.limiter = RateLimiter()
    app.add_middleware(RequestMiddleware, settings=settings)

    @app.exception_handler(AppError)
    async def application_error(request: Request, exc: AppError):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error_response(request, AppError("VALIDATION_ERROR", 422))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        event("db_save_failed", phase="request")
        return error_response(request, AppError("DB_UNAVAILABLE"))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(request, AppError("HTTP_ERROR", exc.status_code))

    register_routes(app)
    app.mount(
        "/assets", StaticFiles(directory=FRONTEND_DIST / "assets", check_dir=False), name="assets"
    )
    return app
