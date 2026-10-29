from sqlalchemy.ext.asyncio import AsyncSession
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuarioUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session, UsuarioRepository.model if hasattr(UsuarioRepository, "model") else __import__("app.modules.usuarios.models", fromlist=["Usuario"]).Usuario)

    async def __aenter__(self) -> "UsuarioUnitOfWork":
        await super().__aenter__()
        self.usuarios = UsuarioRepository(self.session, __import__("app.modules.usuarios.models", fromlist=["Usuario"]).Usuario)
        self.asignaciones = AsignacionRolRepository(self.session, __import__("app.modules.usuarios.models", fromlist=["AsignacionRol"]).AsignacionRol)
        self.intentos = IntentoAccesoRepository(self.session, __import__("app.modules.usuarios.models", fromlist=["IntentoAcceso"]).IntentoAcceso)
        self.eventos = EventoSeguridadRepository(self.session, __import__("app.modules.usuarios.models", fromlist=["EventoSeguridad"]).EventoSeguridad)
        return self


class AccesoUnitOfWork(UnitOfWork):
    """UoW dedicado para intentos de acceso (con su propia transacción aislada si fuera necesario)."""
    async def __aenter__(self) -> "AccesoUnitOfWork":
        await super().__aenter__()
        self.intentos = IntentoAccesoRepository(self.session, __import__("app.modules.usuarios.models", fromlist=["IntentoAcceso"]).IntentoAcceso)
        return self

