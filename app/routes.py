from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse

from app.models import User
from app.schemas import ChatOutput, Credentials, QuestionInput
from app.services import auth, chat

FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
router = APIRouter()


async def authenticated_user(request: Request) -> User:
    return await auth.current_user(request.app.state.db, request.cookies.get("session"))


AuthUser = Annotated[User, Depends(authenticated_user)]


@router.get("/")
async def frontend():
    return FileResponse(FRONTEND_DIST / "index.html")


@router.post("/api/auth/signup", status_code=204)
async def signup(data: Credentials, request: Request):
    await auth.signup(request.app.state.db, data)


@router.post("/api/auth/login", status_code=204)
async def login(data: Credentials, request: Request, response: Response):
    token = await auth.login(request.app.state.db, data)
    response.set_cookie("session", token)


@router.post("/api/auth/logout", status_code=204)
async def logout(request: Request):
    await auth.logout(request.app.state.db, request.cookies.get("session"))
    response = Response(status_code=204)
    response.delete_cookie("session")
    return response


@router.post("/api/chat", response_model=ChatOutput)
async def ask(data: QuestionInput, request: Request, user: AuthUser):
    return await chat.ask(request.app.state.db, request.app.state.ai, user.id, data.question)


@router.get("/api/me/chats", response_model=list[ChatOutput])
async def my_chats(request: Request, user: AuthUser):
    return await chat.history(request.app.state.db, user.id)
