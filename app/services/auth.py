import secrets

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.database import commit
from app.errors import AppError
from app.models import Session, User
from app.schemas import Credentials


async def signup(db, credentials: Credentials):
    async with db.sessions() as session:
        user = User(username=credentials.username, password=credentials.password)
        session.add(user)
        try:
            await commit(session, phase="signup")
        except IntegrityError:
            raise AppError("USERNAME_ALREADY_EXISTS") from None


async def login(db, credentials: Credentials):
    async with db.sessions() as session:
        user = await session.scalar(select(User).where(User.username == credentials.username))
        if not user or user.password != credentials.password:
            raise AppError("INVALID_CREDENTIALS")
        token = secrets.token_urlsafe(32)
        session.add(Session(token=token, user_id=user.id))
        await commit(session, phase="login", user_id=user.id)
        return token


async def current_user(db, token):
    async with db.sessions() as session:
        user = token and await session.scalar(
            select(User).join(Session).where(Session.token == token)
        )
    if not user:
        raise AppError("AUTH_REQUIRED")
    return user


async def logout(db, token):
    async with db.sessions() as session:
        await session.execute(delete(Session).where(Session.token == token))
        await commit(session, phase="logout")
