"""Resolve application resources at the HTTP boundary."""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.database import Database
from app.middleware import RateLimiter
from app.models import User
from app.services.auth import current_user
from app.services.chat import ChatService


def get_database(request: Request) -> Database:
    return request.app.state.db


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_limiter(request: Request) -> RateLimiter:
    return request.app.state.limiter


def get_chat(request: Request) -> ChatService:
    return request.app.state.chat


DatabaseDep = Annotated[Database, Depends(get_database)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_limiter)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat)]


async def authenticated_user(request: Request, db: DatabaseDep) -> User:
    return await current_user(db, request.cookies.get("session"))


AuthUser = Annotated[User, Depends(authenticated_user)]
