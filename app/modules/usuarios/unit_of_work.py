from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session, Usuario)
        self.asignaciones = AsignacionRolRepository(session, AsignacionRol)
        self.intentos = IntentoAccesoRepository(session, IntentoAcceso)
        self.eventos = EventoSeguridadRepository(session, EventoSeguridad)
        self.clientes = ClienteRepository(session, Cliente)


# Compatibilidad con los consumidores existentes del módulo.
UsuarioUnitOfWork = UsuariosUnitOfWork


class AccesoUnitOfWork(UnitOfWork):
    """Excepción de propiedad: crea y cierra una sesión propia por bloque de acceso."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> "AccesoUnitOfWork":
        super().__init__(self.session_factory())
        self.intentos = IntentoAccesoRepository(self.session, IntentoAcceso)
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        # El intento debe sobrevivir al rechazo del login: esta sesión confirma siempre.
        # Costo deliberado: deja filas aunque falle la petición, sin compartir su transacción.
        try:
            await super().__aexit__(None, None, None)
        finally:
            await self.session.close()


async def get_usuarios_uow(
    session: AsyncSession = Depends(get_session),
) -> UsuarioUnitOfWork:
    return UsuarioUnitOfWork(session)


async def get_acceso_uow(request: Request) -> AccesoUnitOfWork:
    return AccesoUnitOfWork(request.app.state.session_factory)
