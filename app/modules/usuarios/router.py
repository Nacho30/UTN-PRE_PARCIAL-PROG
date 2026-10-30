"""Rutas de autenticación (`/auth`)."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import Settings, get_settings
from app.core.dependencies import get_usuario_actual, obtener_payload_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    LoginIn,
    LoginOut,
    LogoutOut,
    RegistroIn,
    UsuarioOut,
    YoOut,
)
from app.modules.usuarios.service import UsuariosService
from app.modules.usuarios.unit_of_work import (
    AccesoUnitOfWork,
    UsuarioUnitOfWork,
    get_acceso_uow,
    get_usuario_uow,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])
service = UsuariosService()


@router.post("/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def registrar(
    data: RegistroIn,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
    settings: Settings = Depends(get_settings),
) -> UsuarioOut:
    return await service.registrar_usuario(uow, data, settings=settings)


@router.post("/login", response_model=LoginOut, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    data: LoginIn,
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
    acceso_uow: AccesoUnitOfWork = Depends(get_acceso_uow),
    settings: Settings = Depends(get_settings),
) -> LoginOut:
    ip = request.client.host if request.client else "0.0.0.0"
    token, salida = await service.login(
        uow=uow,
        acceso_uow=acceso_uow,
        data=data,
        ip=ip,
        hash_ficticio=request.app.state.hash_ficticio,
        settings=settings,
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.jwt_expira_segundos,
    )
    return salida


@router.post("/logout", response_model=LogoutOut, status_code=status.HTTP_200_OK)
async def logout(response: Response) -> LogoutOut:
    response.delete_cookie(key="access_token", httponly=True, samesite="lax")
    return LogoutOut()


@router.get("/yo", response_model=YoOut, status_code=status.HTTP_200_OK)
async def yo(
    usuario: Usuario = Depends(get_usuario_actual),
    payload: dict[str, Any] = Depends(obtener_payload_token),
    uow: UsuarioUnitOfWork = Depends(get_usuario_uow),
) -> YoOut:
    roles_token = payload.get("roles", [])
    return await service.obtener_yo(uow, usuario, roles_token=roles_token)
