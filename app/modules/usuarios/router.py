from fastapi import APIRouter, Depends, Request, Response, status

from app.core.config import get_settings
from app.core.dependencies import UsuarioActual, get_usuario_actual, requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina
from app.core.security import crear_token
from app.core.tipos import IdPath
from app.modules.usuarios.models import Rol
from app.modules.usuarios.schemas import (
    AsignacionCrear,
    AsignacionOut,
    CambiarPasswordIn,
    EventoOut,
    LoginIn,
    PersonalCrear,
    RegistroIn,
    UsuarioActualOut,
    UsuarioOut,
)
from app.modules.usuarios.service import ServiceAuth, UsuariosService
from app.modules.usuarios.unit_of_work import (
    AccesoUnitOfWork, UsuarioUnitOfWork, get_acceso_uow, get_usuarios_uow,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED
)
async def registrar(
    data: RegistroIn, uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    return await ServiceAuth.registrar_usuario(uow, data)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    data: LoginIn,
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
    acceso: AccesoUnitOfWork = Depends(get_acceso_uow),
):
    return await ServiceAuth.login(
        uow=uow,
        acceso=acceso,
        request=request,
        response=response,
        data=data,
        app_state=request.app.state,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    return await ServiceAuth.logout(response)


@router.get("/yo", response_model=UsuarioActualOut)
async def yo(actual: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActualOut:
    usuario = actual.usuario
    return UsuarioActualOut(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        roles=actual.roles,
        activo=usuario.activo,
        roles_vigentes=actual.roles,
        roles_token=actual.roles_token,
        debe_cambiar_password=usuario.debe_cambiar_password,
    )


@router.post("/cambiar-password")
async def cambiar_password(
    data: CambiarPasswordIn,
    response: Response,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    roles = await usuarios_service.cambiar_password(uow, actual.usuario, data)
    settings = get_settings()
    token = crear_token(actual.usuario.email, roles, settings)
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.jwt_expira_segundos,
    )
    return {"mensaje": "Contraseña actualizada"}


personal_router = APIRouter(
    tags=["Usuarios"], dependencies=[Depends(requiere_rol(Rol.ADMIN))]
)
usuarios_service = UsuariosService()


@personal_router.post("/usuarios", response_model=UsuarioOut, status_code=201)
async def crear_personal(
    data: PersonalCrear,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    return await usuarios_service.crear_personal(uow, data, actual.usuario)


@personal_router.get("/usuarios/{id}/roles", response_model=list[AsignacionOut])
async def historial_roles(
    id: IdPath, uow: UsuarioUnitOfWork = Depends(get_usuarios_uow)
):
    return await usuarios_service.historial_roles(uow, id)


@personal_router.post(
    "/usuarios/{id}/roles", response_model=AsignacionOut, status_code=201
)
async def asignar_rol(
    id: IdPath,
    data: AsignacionCrear,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    return await usuarios_service.asignar_rol(uow, id, data, actual.usuario)


@personal_router.delete("/usuarios/{id}/roles/{rol}", response_model=AsignacionOut)
async def revocar_rol(
    id: IdPath,
    rol: Rol,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    return await usuarios_service.revocar_rol(uow, id, rol, actual.usuario)


@personal_router.get("/eventos", response_model=Pagina[EventoOut])
async def eventos(
    params: ParametrosPagina = Depends(),
    uow: UsuarioUnitOfWork = Depends(get_usuarios_uow),
):
    return await usuarios_service.eventos(uow, params)
