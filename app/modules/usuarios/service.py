import math
from datetime import UTC, datetime
from fastapi import Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errores import ErrorDominio
from app.core.security import crear_token, decodificar_token, hash_password, verificar_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Rol, Usuario
from app.modules.usuarios.schemas import LoginIn, RegistroIn, UsuarioOut
from app.modules.usuarios.unit_of_work import AccesoUnitOfWork, UsuarioUnitOfWork


class AuthError(ErrorDominio):
    pass


class ServiceAuth:
    @staticmethod
    async def registrar_usuario(
        session: AsyncSession,
        data: RegistroIn,
        settings: Settings | None = None,
    ) -> UsuarioOut:
        settings = settings or get_settings()
        # 1. Calcular hash ANTES de abrir la transacción principal (o dentro del servicio antes de persistir)
        password_hash = await hash_password(data.password, settings)

        async with UsuarioUnitOfWork(session) as uow:
            # Comprobar si ya existe
            existente = await uow.usuarios.get_by_email(data.email)
            if existente:
                raise ErrorDominio("El correo ya está registrado", status.HTTP_409_CONFLICT)

            usuario = Usuario(
                email=data.email,
                nombre=data.nombre,
                password_hash=password_hash,
                activo=True,
                debe_cambiar_password=False,
            )
            await uow.usuarios.add(usuario)
            await session.flush()

            # Asignar rol CLIENTE
            asignacion = AsignacionRol(
                usuario_id=usuario.id,
                rol=Rol.CLIENTE,
            )
            await uow.asignaciones.add(asignacion)

            # Crear entidad Cliente asociada
            cliente = Cliente(
                usuario_id=usuario.id,
                nombre=data.nombre,
                documento=data.email,  # o por defecto
                telefono="000000000",
            )
            session.add(cliente)
            await session.flush()

            return UsuarioOut(
                id=usuario.id,
                email=usuario.email,
                nombre=usuario.nombre,
                roles=[Rol.CLIENTE],
                activo=usuario.activo,
            )

    @staticmethod
    async def login(
        session_factory,
        request: Request,
        response: Response,
        data: LoginIn,
        app_state,
        settings: Settings | None = None,
    ):
        settings = settings or get_settings()
        ip = request.client.host if request.client else "0.0.0.0"

        # 1. AccesoUnitOfWork (sesión propia): contar fallos de (email, ip) en 60s posteriores al último éxito
        async with session_factory() as acc_session:
            async with AccesoUnitOfWork(acc_session) as acc_uow:
                # Comprobar límite de intentos
                fallos_count = await acc_uow.intentos.contar_fallos_recientes(data.email, ip, settings.LOGIN_VENTANA_SEGUNDOS)
                if fallos_count >= settings.LOGIN_MAX_FALLOS:
                    quinto = await acc_uow.intentos.get_quinto_fallo(data.email, ip)
                    retry_after = 60
                    if quinto:
                        ahora_dt = datetime.now(quinto.cuando.tzinfo or UTC)
                        delta = (quinto.cuando + __import__("datetime").timedelta(seconds=60)) - ahora_dt
                        retry_after = max(1, math.ceil(delta.total_seconds()))
                    
                    response.headers["Retry-After"] = str(retry_after)
                    raise ErrorDominio("Demasiados intentos fallidos. Intente más tarde.", status.HTTP_429_TOO_MANY_REQUESTS)

        # 2. UoW de la petición: leer el usuario por email
        usuario = None
        async with session_factory() as uow_session:
            async with UsuarioUnitOfWork(uow_session) as uow:
                usuario = await uow.usuarios.get_by_email(data.email)
                # Cargar roles vigentes
                roles_vigentes = []
                if usuario:
                    from sqlalchemy import select
                    stmt_roles = select(AsignacionRol.rol).where(
                        AsignacionRol.usuario_id == usuario.id,
                        AsignacionRol.revocada_en.is_(None),
                    )
                    res_roles = await uow_session.execute(stmt_roles)
                    roles_vigentes = list(res_roles.scalars().all())

        # 3. bcrypt.checkpw en to_thread + semáforo, SIN transacción abierta
        hash_a_verificar = usuario.password_hash if usuario and usuario.activo else app_state.hash_ficticio
        exito = await verificar_password(data.password, hash_a_verificar)
        if not usuario or not usuario.activo:
            exito = False

        # 4. AccesoUnitOfWork: anotar el intento
        async with session_factory() as acc_session:
            async with AccesoUnitOfWork(acc_session) as acc_uow:
                intento = IntentoAcceso(email=data.email, ip=ip, exito=exito)
                await acc_uow.intentos.add(intento)

        if not exito:
            raise ErrorDominio("Correo o contraseña incorrectos", status.HTTP_401_UNAUTHORIZED)

        # 6. Roles vigentes → JWT → Set-Cookie
        token = crear_token(sub=usuario.email, roles=roles_vigentes, settings=settings)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=settings.COOKIE_SECURE,
            max_age=settings.jwt_expira_segundos,
        )
        return {"mensaje": "Login exitoso"}

    @staticmethod
    async def logout(response: Response):
        response.delete_cookie(key="access_token")
        return {"mensaje": "Logout exitoso"}
