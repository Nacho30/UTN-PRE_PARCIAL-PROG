"""Repositorios del módulo de usuarios, roles, intentos de acceso y eventos."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Rol,
    Usuario,
)


def _vigente(momento: datetime):
    return (
        AsignacionRol.revocada_en.is_(None),
        AsignacionRol.desde <= momento,
        or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > momento),
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

    async def get_roles_vigentes(
        self,
        usuario_id: int,
        ahora: datetime | None = None,
    ) -> list[Rol]:
        """Devuelve los roles vigentes del usuario (no revocados, iniciados y sin vencer)."""
        momento = ahora or datetime.now(UTC)
        roles = await self.get_vigentes_de_usuario(usuario_id, momento)
        return [Rol(r) for r in roles]

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


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    async def get_fallos_recientes(
        self,
        email: str,
        ip: str,
        ventana_segundos: int = 60,
        limite: int = 5,
        ahora: datetime | None = None,
    ) -> list[IntentoAcceso]:
        """Obtiene los intentos fallidos dentro de la ventana y posteriores al último éxito.

        Se ordenan del más nuevo al más viejo con LIMIT 5 (diseño RN-08): si hay 5, el quinto
        elemento es el que debe salir de la ventana para volver a habilitar el login.
        """
        momento = ahora or datetime.now(UTC)
        desde = momento - timedelta(seconds=ventana_segundos)

        ultimo_exito_subq = (
            select(func.max(IntentoAcceso.cuando))
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .scalar_subquery()
        )

        stmt = (
            select(IntentoAcceso)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(False),
                IntentoAcceso.cuando >= desde,
                IntentoAcceso.cuando <= momento,
                or_(
                    ultimo_exito_subq.is_(None),
                    IntentoAcceso.cuando > ultimo_exito_subq,
                ),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(limite)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def contar_fallos_recientes(
        self,
        email: str,
        ip: str,
        ventana_segundos: int = 60,
        ahora: datetime | None = None,
    ) -> int:
        """Cuenta los intentos fallidos vigentes en la ventana posteriores al último éxito."""
        momento = ahora or datetime.now(UTC)
        desde = momento - timedelta(seconds=ventana_segundos)

        ultimo_exito_subq = (
            select(func.max(IntentoAcceso.cuando))
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .scalar_subquery()
        )

        stmt = (
            select(func.count())
            .select_from(IntentoAcceso)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(False),
                IntentoAcceso.cuando >= desde,
                IntentoAcceso.cuando <= momento,
                or_(
                    ultimo_exito_subq.is_(None),
                    IntentoAcceso.cuando > ultimo_exito_subq,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_quinto_fallo(
        self,
        email: str,
        ip: str,
        ventana_segundos: int = 60,
        ahora: datetime | None = None,
    ) -> IntentoAcceso | None:
        """Devuelve el quinto intento fallido más reciente dentro de la ventana vigente."""
        fallos = await self.get_fallos_recientes(
            email=email,
            ip=ip,
            ventana_segundos=ventana_segundos,
            limite=5,
            ahora=ahora,
        )
        if len(fallos) >= 5:
            return fallos[4]
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
