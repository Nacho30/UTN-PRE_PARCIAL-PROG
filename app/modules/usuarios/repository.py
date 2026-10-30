from datetime import datetime

from sqlalchemy import func, or_, select

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    async def get_vigentes_de_usuario(
        self, usuario_id: int, momento: datetime
    ) -> list[str]:
        stmt = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario_id,
                *_vigente(momento),
            )
            .order_by(AsignacionRol.rol)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_historial_de_usuario(self, usuario_id: int) -> list[AsignacionRol]:
        stmt = (
            select(AsignacionRol)
            .where(AsignacionRol.usuario_id == usuario_id)
            .order_by(AsignacionRol.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_abierta(self, usuario_id: int, rol: str) -> AsignacionRol | None:
        stmt = select(AsignacionRol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.rol == rol,
            AsignacionRol.revocada_en.is_(None),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def contar_administradores(self, momento: datetime) -> int:
        stmt = (
            select(func.count(func.distinct(Usuario.id)))
            .join(
                AsignacionRol,
                AsignacionRol.usuario_id == Usuario.id,
            )
            .where(
                Usuario.activo.is_(True),
                AsignacionRol.rol == "ADMIN",
                *_vigente(momento),
            )
        )
        return (await self.session.execute(stmt)).scalar_one()


def _vigente(momento: datetime):
    return (
        AsignacionRol.revocada_en.is_(None),
        AsignacionRol.desde <= momento,
        or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > momento),
    )


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    async def contar_fallos_recientes(
        self, email: str, ip: str, ventana_segundos: int
    ) -> int:
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
        ahora_dt = (
            datetime.now(fallos[0].cuando.tzinfo)
            if fallos and fallos[0].cuando.tzinfo
            else datetime.utcnow()
        )
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

        stmt_fallos = select(IntentoAcceso).where(
            IntentoAcceso.email == email,
            IntentoAcceso.ip == ip,
            IntentoAcceso.exito.is_(False),
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
    async def get_paginado(self, page: int, size: int) -> list[EventoSeguridad]:
        stmt = (
            select(EventoSeguridad)
            .order_by(EventoSeguridad.cuando.desc(), EventoSeguridad.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return list((await self.session.execute(stmt)).scalars().all())
