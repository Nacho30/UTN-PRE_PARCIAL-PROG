"""Aplicación, lifespan y los dos grupos de rutas.

Grupo ABIERTO: /health (y /auth, en el ejercicio 4). Grupo PROTEGIDO: el resto de los
módulos; en el ejercicio 5 lleva montado, una sola vez, el control del cambio obligatorio
de contraseña. FastAPI suma dependencias y no las resta (sección 5.10).
"""

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from app import modelos  # noqa: F401  registra todos los modelos antes de configurar los mappers
from app.core.config import get_settings
from app.core.database import crear_engine, crear_session_factory
from app.core.security import hash_password
from app.modules.health.router import router as health_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("taller")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Todo se crea acá, ya dentro del bucle de eventos, y no al importar (EA-08, sección 1.9).
    settings = get_settings()
    engine = crear_engine(settings)
    app.state.engine = engine
    app.state.session_factory = crear_session_factory(engine)
    # Hash ficticio, calculado una sola vez y con el mismo costo que los reales: el login
    # (ejercicio 4) verifica contra él cuando el correo no existe, y así tarda lo mismo.
    app.state.hash_ficticio = await hash_password(secrets.token_urlsafe(32), settings)
    logger.info("Taller listo (pool=%s, bcrypt=%s)", settings.DB_POOL_SIZE, settings.BCRYPT_ROUNDS)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title="Taller mecánico",
    description="Órdenes de trabajo, stock y acceso con FastAPI y PostgreSQL",
    version="0.2.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def error_no_previsto(request: Request, exc: Exception) -> JSONResponse:
    # Nunca una traza ni texto de la base hacia el cliente. La traza va al registro.
    logger.exception("Error no previsto en %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Error interno del servidor"}, status_code=500)


abierto = APIRouter()
abierto.include_router(health_router)

protegido = APIRouter()  # los routers de los módulos se incluyen acá a partir del ejercicio 3

app.include_router(abierto)
app.include_router(protegido)
