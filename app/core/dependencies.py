"""Dependencias de autenticación y autorización.

En el ejercicio 4 se implementan la lectura exclusiva del token desde la cookie `access_token`
(nunca desde `Authorization: Bearer`) y `get_usuario_actual` con todas las causas de 401,
incluyendo la comparación sin truncar en microsegundos enteros de `iat` contra
`password_cambiada_en` (RN-07).
"""

from datetime import UTC
from typing import Any

from fastapi import Depends, Request
import jwt

from app.core.database import lectura_corta
from app.core.errores import ErrorNoAutenticado
from app.core.security import decodificar_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork, get_usuario_uow


async def obtener_token_cookie(request: Request) -> str:
    """Lee el JWT exclusivamente desde la cookie `access_token`.

    La cabecera `Authorization` no se lee nunca (RN-09 / requisito de cookie HttpOnly).
    """
    token = request.cookies.get("access_token")
    if not token:
        raise ErrorNoAutenticado("No autenticado")
    return token


async def obtener_payload_token(
    token: str = Depends(obtener_token_cookie),
) -> dict[str, Any]:
    """Decodifica y verifica la firma y vigencia del JWT."""
    try:
        return decodificar_token(token)
    except jwt.PyJWTError as exc:
        raise ErrorNoAutenticado("Token inválido o vencido") from exc
    except Exception as exc:
        raise ErrorNoAutenticado("Token inválido o vencido") from exc


async def get_usuario_actual(
    request: Request,
    payload: dict[str, Any] = Depends(obtener_payload_token),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> Usuario:
    """Obtiene el usuario autenticado y verifica que la sesión siga siendo válida (401).

    Causas de 401:
    - Sin cookie `access_token` (incluso si envía `Authorization: Bearer`).
    - Token inválido o vencido (`exp`).
    - Usuario inexistente o con `activo = False`.
    - Token emitido antes de `password_cambiada_en` comparado en microsegundos enteros (RN-07).
    """
    sub = payload.get("sub")
    iat = payload.get("iat")
    if sub is None or iat is None:
        raise ErrorNoAutenticado("Token inválido o vencido")

    async with lectura_corta(uow.session):
        sub_str = str(sub)
        if "@" in sub_str:
            usuario = await uow.usuarios.get_by_email(sub_str)
        elif sub_str.isdigit():
            usuario = await uow.usuarios.get_by_id(int(sub_str))
        else:
            usuario = await uow.usuarios.get_by_email(sub_str)

    if usuario is None or not usuario.activo:
        raise ErrorNoAutenticado("Usuario no encontrado o inactivo")

    if usuario.password_cambiada_en is not None:
        cambiada_en = usuario.password_cambiada_en
        if cambiada_en.tzinfo is None:
            cambiada_en = cambiada_en.replace(tzinfo=UTC)
        iat_us = round(float(iat) * 1_000_000)
        cambiada_us = round(cambiada_en.timestamp() * 1_000_000)
        if iat_us < cambiada_us:
            raise ErrorNoAutenticado("La sesión caducó por cambio de contraseña")

    request.state.token_payload = payload
    return usuario
