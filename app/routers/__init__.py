"""One place to register HTML, health, and versionless /api routes."""

from fastapi import APIRouter, FastAPI

from app.routers import auth, conversations, health, me, pages


def register_routes(app: FastAPI) -> None:
    api = APIRouter(prefix="/api")
    for router in (auth.router, conversations.router, me.router):
        api.include_router(router)
    app.include_router(api)
    app.include_router(pages.router)
    app.include_router(health.router)
