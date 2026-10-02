from fastapi import APIRouter, Request, Response

from app.dependencies import AuthUser, DatabaseDep, RateLimiterDep, SettingsDep
from app.schemas import Credentials, UserOutput
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/signup", status_code=201, response_model=UserOutput)
async def signup(data: Credentials, request: Request, db: DatabaseDep, limiter: RateLimiterDep):
    limiter.check(("signup", client_ip(request)))
    return await auth.signup(db, data)


@router.post("/login", response_model=UserOutput)
async def login(
    data: Credentials,
    request: Request,
    response: Response,
    db: DatabaseDep,
    settings: SettingsDep,
    limiter: RateLimiterDep,
):
    limiter.check(("login", client_ip(request)))
    user, token = await auth.login(db, settings, data, request.cookies.get("session"))
    response.set_cookie(
        "session",
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=204)
async def logout(request: Request, user: AuthUser, db: DatabaseDep, settings: SettingsDep):
    await auth.logout(db, request.cookies["session"])
    response = Response(status_code=204)
    response.delete_cookie(
        "session", path="/", httponly=True, secure=settings.cookie_secure, samesite="lax"
    )
    return response
