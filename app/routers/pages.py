from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.dependencies import DatabaseDep
from app.errors import AppError
from app.services.auth import current_user

router = APIRouter()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def frontend():
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return HTMLResponse(
            "프런트엔드 빌드가 필요합니다: pnpm --dir frontend build", status_code=503
        )
    return FileResponse(index)


@router.get("/", name="pages:home")
async def home(request: Request):
    return RedirectResponse(request.url_for("pages:chat"), status_code=303)


@router.get("/login", name="pages:login")
async def login():
    return frontend()


@router.get("/signup", name="pages:signup")
async def signup():
    return frontend()


@router.get("/chat", name="pages:chat")
async def chat(request: Request, db: DatabaseDep):
    try:
        await current_user(db, request.cookies.get("session"))
    except AppError as exc:
        if exc.status == 401:
            return RedirectResponse(request.url_for("pages:login"), status_code=303)
        raise
    return frontend()
