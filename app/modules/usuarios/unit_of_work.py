"""Unit of Work del módulo de usuarios y de intentos de acceso."""

from collections.abc import Callable
from typing import Any, Self

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuarioUnitOfWork(UnitOfWork):
    """Compone los repositorios de usuarios, roles, eventos y clientes sobre la misma sesión.

    Incluye `clientes: ClienteRepository` para que el auto-registro (`POST /auth/registro`,
    RN-02) cree `Usuario`, `AsignacionRol(rol=Rol.CLIENTE)` y `Cliente` en una única
    transacción atómica: las tres filas se confirman juntas o se revierten juntas.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session, Usuario)
        self.asignaciones = AsignacionRolRepository(session, AsignacionRol)
        self.clientes = ClienteRepository(session, Cliente)
        self.intentos = IntentoAccesoRepository(session, IntentoAcceso)
        self.eventos = EventoSeguridadRepository(session, EventoSeguridad)


UsuariosUnitOfWork = UsuarioUnitOfWork


class AccesoUnitOfWork:
    """UoW dedicado para `intento_acceso` con sesión y transacción propias (Ejercicio 7, sección 6.8.1).

    Por qué usa una sesión y transacción propias que se confirman siempre:
    - El intento de acceso que más importa registrar y contar para el límite de `RN-08` es
      precisamente el intento **fallido**, el cual termina lanzando `401 Unauthorized`.
    - Si `IntentoAcceso` se anotara en la misma sesión/transacción de la petición principal,
      al revertirse (`rollback`) por el error 401 también se revertiría la fila de
      `intento_acceso` y nunca se acumularían los 5 fallos.

    Costo / contrapartida de esta decisión:
    - Cada intento de login toma una sesión propia desde `session_factory`, ejecuta su propio
      `commit()` y la cierra inmediatamente, dejando filas persistidas en `intento_acceso`
      aunque la petición de login falle y sea rechazada.
    """

    def __init__(
        self,
        session_or_factory: Callable[[], AsyncSession] | AsyncSession,
    ) -> None:
        if callable(session_or_factory):
            self._session_factory: Callable[[], AsyncSession] | None = session_or_factory
            self.session: AsyncSession | None = None
            self._owns_session = True
        else:
            self._session_factory = None
            self.session = session_or_factory
            self._owns_session = False
            self.intentos = IntentoAccesoRepository(self.session, IntentoAcceso)

    async def __aenter__(self) -> Self:
        if self._owns_session and self._session_factory is not None:
            self.session = self._session_factory()
        assert self.session is not None
        self.intentos = IntentoAccesoRepository(self.session, IntentoAcceso)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.session is None:
            return
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            if self._owns_session:
                await self.session.close()


async def get_usuario_uow(session: AsyncSession = Depends(get_session)) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)


get_usuarios_uow = get_usuario_uow


async def get_acceso_uow(request: Request) -> AccesoUnitOfWork:
    return AccesoUnitOfWork(request.app.state.session_factory)
