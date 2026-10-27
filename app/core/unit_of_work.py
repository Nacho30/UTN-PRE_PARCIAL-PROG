"""`UnitOfWork` base: confirma o revierte al salir del bloque transaccional.

El Unit of Work no cierra la sesión: la sesión fue creada y es cerrada por la
dependencia `get_session` (sección 1.9 y arquitectura de capas).
"""

from typing import Self
from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Gestor de contexto asincrónico para transacciones en un solo bloque."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if exc_type is not None:
            await self.session.rollback()
        else:
            await self.session.commit()
