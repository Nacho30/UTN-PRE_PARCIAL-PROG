from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decodificar_token, verificar_password
from app.modules.usuarios.schemas import LoginIn, RegistroIn, UsuarioOut
from app.modules.usuarios.service import ServiceAuth
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork
from app.core.errores import ErrorDominio

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def registrar(data: RegistroIn, session: AsyncSession = Depends(get_session)):
    return await ServiceAuth.registrar_usuario(session, data)


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    data: LoginIn,
    session_factory=Depends(lambda: request.app.state.session_factory),
):
    return await ServiceAuth.login(
        session_factory=session_factory,
        request=request,
        response=response,
        data=data,
        app_state=request.app.state,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    return await ServiceAuth.logout(response)


@router.get("/yo", response_model=UsuarioOut, status_code=status.HTTP_200_OK)
async def yo(
    request: Request,
    access_token: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
):
    if not access_token:
        raise ErrorDominio("No autenticado", status.HTTP_401_UNAUTHORIZED)
    
    try:
        payload = decodificar_token(access_token)
    except Exception:
        raise ErrorDominio("Token inválido o expirado", status.HTTP_401_UNAUTHORIZED)

    email = payload.get("sub")
    roles_token = payload.get("roles", [])

    async with UsuarioUnitOfWork(session) as uow:
        usuario = await uow.usuarios.get_by_email(email)
        if not usuario or not usuario.activo:
            raise ErrorDominio("Usuario no encontrado o inactivo", status.HTTP_401_UNAUTHORIZED)

        from sqlalchemy import select
        from app.modules.usuarios.models import AsignacionRol
        stmt_roles = select(AsignacionRol.rol).where(
            AsignacionRol.usuario_id == usuario.id,
            AsignacionRol.revocada_en.is_(None),
        )
        res_roles = await session.execute(stmt_roles)
        roles_vigentes = list(res_roles.scalars().all())

        return UsuarioOut(
            id=usuario.id,
            email=usuario.email,
            nombre=usuario.nombre,
            roles=roles_vigentes,
            activo=usuario.activo,
        )
