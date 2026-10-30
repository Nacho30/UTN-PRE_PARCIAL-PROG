"""Motor, fábrica de sesiones y `get_session`.

Nada de esto se construye al importar el módulo (EA-08, sección 1.9): un motor creado al
importar nace antes de que exista el bucle de eventos, y el síntoma —anda al levantar el
servidor y falla en las pruebas, o al revés— no señala la causa. El lifespan llama a
`crear_engine` y `crear_session_factory` y guarda el resultado en `app.state`.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


def crear_engine(settings: Settings) -> AsyncEngine:
    # SQL_ECHO=true muestra cada consulta en la consola (evidencia de C-15). No se usa
    # `echo=True`: ese parámetro le agrega a SQLAlchemy un handler propio y, como el registro
    # de la aplicación ya escribe en la consola, cada consulta salía dos veces. Subir el
    # nivel del logger alcanza para que salga una sola vez, con el formato de la aplicación.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.SQL_ECHO else logging.WARNING
    )
    return create_async_engine(
        settings.database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


def crear_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: después del commit los objetos se siguen pudiendo leer
    # sin disparar una consulta (en asincrónico, esa consulta escondida falla).
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Una sesión por petición. La crea y la cierra esta dependencia, nadie más."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


@asynccontextmanager
async def lectura_corta(session: AsyncSession) -> AsyncIterator[None]:
    """Transacción de sólo lectura que termina al salir del bloque.

    La usan las dependencias de autorización: leen el usuario y sus roles y devuelven la
    conexión al pool, para que el servicio no la tenga tomada mientras corre bcrypt.
    Si ya hay una transacción abierta, no abre otra.
    """
    if session.in_transaction():
        yield
        return
    async with session.begin():
        yield
