"""Sondas de salud.

El proceso puede estar vivo y no estar listo: `live` sólo dice que el servidor responde (no
toca la base), y `ready` dice si puede atender (`SELECT 1`). Si la base está caída, `ready`
da 503 y `live` sigue en 200: reiniciar el proceso no arregla una base caída.
"""

import asyncio
import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger("taller.health")


@router.get("/live")
async def live() -> dict[str, str]:
    return {"estado": "vivo"}


async def _select_1(request: Request) -> None:
    async with request.app.state.session_factory() as session:
        await session.execute(text("SELECT 1"))


@router.get("/ready", responses={503: {"description": "La base no contesta"}})
async def ready(request: Request) -> JSONResponse:
    try:
        await asyncio.wait_for(_select_1(request), timeout=3)
    except Exception:  # cualquier falla de conexión, de driver o de tiempo
        logger.warning("La base no contesta", exc_info=True)
        return JSONResponse(
            {"estado": "no listo", "detail": "La base de datos no contesta"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return JSONResponse({"estado": "listo"})
