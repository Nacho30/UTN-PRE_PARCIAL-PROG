from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    pass


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    async def contar_fallos_recientes(self, email: str, ip: str, ventana_segundos: int) -> int:
        # Contar fallos recientes posteriores al último éxito o en la ventana temporal
        # Según diseño: contar fallos de (email, ip) en 60 s, posteriores al último éxito.
        # Primero buscamos el último éxito:
        stmt_exito = (
            select(IntentoAcceso.cuando)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(1)
        )
        res_exito = await self.session.execute(stmt_exito)
        ultimo_exito = res_exito.scalars().first()

        stmt_fallos = select(IntentoAcceso).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
        )
        if ultimo_exito:
            stmt_fallos = stmt_fallos.where(IntentoAcceso.cuando > ultimo_exito)

        result = await self.session.execute(stmt_fallos)
        fallos = result.scalars().all()

        # Filtrar también por ventana de tiempo (ej. últimos 60 segundos)
        ahora_dt = datetime.now(fallos[0].cuando.tzinfo) if fallos and fallos[0].cuando.tzinfo else datetime.utcnow()
        # Contamos cuántos caen en la ventana
        # O simplemente traer del más nuevo al más viejo para calcular Retry-After
        return len(fallos)

    async def get_quinto_fallo(self, email: str, ip: str) -> IntentoAcceso | None:
        stmt_exito = (
            select(IntentoAcceso.cuando)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(1)
        )
        res_exito = await self.session.execute(stmt_exito)
        ultimo_exito = res_exito.scalars().first()

        stmt_fallos = (
            select(IntentoAcceso)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(False),
            )
        )
        if ultimo_exito:
            stmt_fallos = stmt_fallos.where(IntentoAcceso.cuando > ultimo_exito)

        stmt_fallos = stmt_fallos.order_by(IntentoAcceso.cuando.desc()).limit(5)
        result = await self.session.execute(stmt_fallos)
        fallos = result.scalars().all()
        if len(fallos) >= 5:
            return fallos[4]  # el quinto más viejo de los últimos 5
        return None


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    pass

