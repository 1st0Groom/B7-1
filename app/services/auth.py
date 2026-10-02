import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool

from app.database import commit
from app.errors import AppError
from app.models import Session, User, utcnow
from app.schemas import Credentials

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("dummy-account-password")


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


async def signup(db, credentials: Credentials):
    password_hash = await run_in_threadpool(hasher.hash, credentials.password)
    async with db.sessions() as session:
        user = User(username=credentials.username, password_hash=password_hash)
        session.add(user)
        try:
            await commit(session, phase="signup")
        except IntegrityError:
            raise AppError("USERNAME_ALREADY_EXISTS", 409) from None
        return {"id": user.id, "username": user.username}


async def login(db, settings, credentials: Credentials, old_token):
    async with db.sessions() as session:
        user = await session.scalar(select(User).where(User.username == credentials.username))
    encoded = user.password_hash if user else DUMMY_HASH
    try:
        await run_in_threadpool(hasher.verify, encoded, credentials.password)
    except (VerificationError, InvalidHashError):
        raise AppError("INVALID_CREDENTIALS", 401) from None
    if not user:
        raise AppError("INVALID_CREDENTIALS", 401)
    token = secrets.token_urlsafe(32)
    async with db.sessions() as session:
        await session.execute(delete(Session).where(Session.expires_at <= utcnow()))
        if old_token:
            await session.execute(
                delete(Session).where(Session.token_hash == token_hash(old_token))
            )
        session.add(
            Session(
                token_hash=token_hash(token),
                user_id=user.id,
                expires_at=utcnow() + timedelta(seconds=settings.session_ttl_seconds),
            )
        )
        await commit(session, phase="login", user_id=user.id)
    return {"id": user.id, "username": user.username}, token


async def current_user(db, token):
    if not token or len(token) > 256:
        raise AppError("AUTH_REQUIRED", 401)
    async with db.sessions() as session:
        user = await session.scalar(
            select(User)
            .join(Session)
            .where(Session.token_hash == token_hash(token), Session.expires_at > utcnow())
        )
    if not user:
        raise AppError("AUTH_REQUIRED", 401)
    return user


async def logout(db, token):
    async with db.sessions() as session:
        await session.execute(delete(Session).where(Session.token_hash == token_hash(token)))
        await commit(session, phase="logout")
