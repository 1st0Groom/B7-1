from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import DatabaseDep

router = APIRouter(prefix="/health")


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: DatabaseDep):
    try:
        async with db.sessions() as session:
            await session.execute(text("SELECT id FROM users LIMIT 1"))
            await session.execute(text("SELECT id FROM chat_turns LIMIT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}
