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


class UsuarioRepository(BaseRepository[Usuario]):
    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    async def get_roles_vigentes(
        self,
        usuario_id: int,
        ahora: datetime | None = None,
    ) -> list[Rol]:
        """Devuelve los roles vigentes del usuario (no revocados y sin vencer)."""
        momento = ahora or datetime.now(UTC)
        stmt = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario_id,
            AsignacionRol.revocada_en.is_(None),
            or_(
                AsignacionRol.vence_en.is_(None),
                AsignacionRol.vence_en > momento,
            ),
        )
        result = await self.session.execute(stmt)
        return [Rol(r) for r in result.scalars().all()]


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
    pass
