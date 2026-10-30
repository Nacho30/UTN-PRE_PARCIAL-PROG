"""Identidad desde cookie y permisos vigentes consultados en cada petición."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

import jwt
from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session, lectura_corta
from app.core.errores import ErrorNoAutenticado, ErrorPermiso
from app.core.security import decodificar_token
from app.core.tipos import ahora
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.repository import AsignacionRolRepository, UsuarioRepository


@dataclass
class UsuarioActual:
    usuario: Usuario
    roles: list[str]
    roles_token: list[str]


def _microsegundos(momento: datetime) -> int:
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    delta = momento.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


async def get_roles_vigentes(session: AsyncSession, usuario_id: int) -> list[str]:
    return await AsignacionRolRepository(
        session, AsignacionRol
    ).get_vigentes_de_usuario(usuario_id, ahora())


async def get_usuario_actual(
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> UsuarioActual:
    if not access_token:
        raise ErrorNoAutenticado()
    try:
        payload = decodificar_token(access_token)
        iat = Decimal(str(payload["iat"]))
        if not iat.is_finite():
            raise ValueError("iat inválido")
        iat_us = int(iat * 1_000_000)
    except (
        jwt.InvalidTokenError,
        ValueError,
        TypeError,
        InvalidOperation,
        OverflowError,
    ):
        raise ErrorNoAutenticado("Token inválido o expirado") from None
    async with lectura_corta(session):
        usuario = await UsuarioRepository(session, Usuario).get_by_email(payload["sub"])
        if usuario is None or not usuario.activo:
            raise ErrorNoAutenticado()
        if usuario.password_cambiada_en and iat_us < _microsegundos(
            usuario.password_cambiada_en
        ):
            raise ErrorNoAutenticado("La sesión es anterior al cambio de contraseña")
        roles = await get_roles_vigentes(session, usuario.id)  # type: ignore[arg-type]
    return UsuarioActual(usuario, roles, payload.get("roles", []))


def requiere_rol(*roles: str):
    async def comprobar(
        actual: UsuarioActual = Depends(get_usuario_actual),
    ) -> UsuarioActual:
        if not set(actual.roles).intersection(roles):
            raise ErrorPermiso()
        return actual

    return comprobar


async def exigir_password_al_dia(
    actual: UsuarioActual = Depends(get_usuario_actual),
) -> None:
    if actual.usuario.debe_cambiar_password:
        raise ErrorPermiso("Debe cambiar la contraseña antes de continuar")
