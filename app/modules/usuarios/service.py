import math
from datetime import UTC, datetime

from fastapi import Request, Response, status

from app.core.config import Settings, get_settings
from app.core.errores import (
    ErrorConflicto,
    ErrorDominio,
    ErrorNoAutenticado,
    ErrorNoEncontrado,
)
from app.core.paginacion import Pagina, ParametrosPagina, calcular_paginacion
from app.core.security import (
    crear_token,
    hash_password,
    verificar_password,
)
from app.core.tipos import ahora
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Rol,
    Usuario,
)
from app.modules.usuarios.schemas import (
    AsignacionCrear,
    AsignacionOut,
    CambiarPasswordIn,
    EventoOut,
    LoginIn,
    PersonalCrear,
    RegistroIn,
    UsuarioOut,
)
from app.modules.usuarios.unit_of_work import AccesoUnitOfWork, UsuarioUnitOfWork


class AuthError(ErrorDominio):
    pass


class ServiceAuth:
    @staticmethod
    async def registrar_usuario(
        uow: UsuarioUnitOfWork,
        data: RegistroIn,
        settings: Settings | None = None,
    ) -> UsuarioOut:
        settings = settings or get_settings()
        # 1. Calcular hash ANTES de abrir la transacción principal (o dentro del servicio antes de persistir)
        password_hash = await hash_password(data.password, settings)
        async with uow:
            usuario = Usuario(
                email=data.email,
                nombre=data.nombre,
                password_hash=password_hash,
                activo=True,
                debe_cambiar_password=False,
            )
            await uow.usuarios.add(usuario)
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
                documento=data.documento,
                telefono=data.telefono,
            )
            await uow.clientes.add(cliente)
            await uow.eventos.add(
                EventoSeguridad(actor=usuario.email, accion="Alta de cliente")
            )
            return UsuarioOut(
                id=usuario.id,
                email=usuario.email,
                nombre=usuario.nombre,
                roles=[Rol.CLIENTE],
                activo=usuario.activo,
            )

    @staticmethod
    async def login(
        uow: UsuarioUnitOfWork,
        acceso: AccesoUnitOfWork,
        request: Request,
        response: Response,
        data: LoginIn,
        app_state,
        settings: Settings | None = None,
    ):
        settings = settings or get_settings()
        ip = request.client.host if request.client else "0.0.0.0"
        # 1. AccesoUnitOfWork (sesión propia): contar fallos de (email, ip) en 60s posteriores al último éxito
        async with acceso:
            # Comprobar límite de intentos
            fallos_count = await acceso.intentos.contar_fallos_recientes(
                data.email, ip, settings.LOGIN_VENTANA_SEGUNDOS
            )
            if fallos_count >= settings.LOGIN_MAX_FALLOS:
                quinto = await acceso.intentos.get_quinto_fallo(data.email, ip)
                retry_after = 60
                if quinto:
                    ahora_dt = datetime.now(quinto.cuando.tzinfo or UTC)
                    delta = (
                        quinto.cuando + __import__("datetime").timedelta(seconds=60)
                    ) - ahora_dt
                    retry_after = max(1, math.ceil(delta.total_seconds()))

                response.headers["Retry-After"] = str(retry_after)
                raise ErrorDominio(
                    "Demasiados intentos fallidos. Intente más tarde.",
                    status.HTTP_429_TOO_MANY_REQUESTS,
                )
        # 2. UoW de la petición: leer el usuario por email
        usuario = None
        async with uow:
            usuario = await uow.usuarios.get_by_email(data.email)
            roles_vigentes = (
                await uow.asignaciones.get_vigentes_de_usuario(usuario.id, ahora())
                if usuario
                else []
            )
        # 3. bcrypt.checkpw en to_thread + semáforo, SIN transacción abierta
        hash_a_verificar = (
            usuario.password_hash
            if usuario and usuario.activo
            else app_state.hash_ficticio
        )
        exito = await verificar_password(data.password, hash_a_verificar)
        if not usuario or not usuario.activo:
            exito = False
        # 4. AccesoUnitOfWork: anotar el intento
        async with acceso:
            intento = IntentoAcceso(email=data.email, ip=ip, exito=exito)
            await acceso.intentos.add(intento)
        if not exito:
            raise ErrorDominio(
                "Correo o contraseña incorrectos", status.HTTP_401_UNAUTHORIZED
            )
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


class UsuariosService:
    async def crear_personal(
        self, uow: UsuarioUnitOfWork, data: PersonalCrear, actor: Usuario
    ) -> UsuarioOut:
        password_hash = await hash_password(data.password)
        async with uow:
            usuario = Usuario(
                email=data.email,
                nombre=data.nombre,
                password_hash=password_hash,
                debe_cambiar_password=True,
            )
            await uow.usuarios.add(usuario)
            for rol in data.roles:
                await uow.asignaciones.add(
                    AsignacionRol(usuario_id=usuario.id, rol=rol, otorgada_por=actor.id)
                )
            await uow.eventos.add(
                EventoSeguridad(
                    actor=actor.email, accion=f"Alta de personal {usuario.email}"
                )
            )
            return UsuarioOut(
                id=usuario.id,
                email=usuario.email,
                nombre=usuario.nombre,
                roles=data.roles,
                activo=usuario.activo,
            )

    async def _exigir_usuario(self, uow: UsuarioUnitOfWork, usuario_id: int) -> Usuario:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise ErrorNoEncontrado(f"No existe el usuario con id {usuario_id}")
        return usuario

    def _asignacion_out(
        self, asignacion: AsignacionRol, momento: datetime
    ) -> AsignacionOut:
        vigente = (
            asignacion.revocada_en is None
            and asignacion.desde <= momento
            and (asignacion.vence_en is None or asignacion.vence_en > momento)
        )
        return AsignacionOut(**asignacion.model_dump(), vigente=vigente)

    async def historial_roles(
        self, uow: UsuarioUnitOfWork, usuario_id: int
    ) -> list[AsignacionOut]:
        async with uow:
            await self._exigir_usuario(uow, usuario_id)
            filas = await uow.asignaciones.get_historial_de_usuario(usuario_id)
            momento = ahora()
            return [self._asignacion_out(fila, momento) for fila in filas]

    async def asignar_rol(
        self,
        uow: UsuarioUnitOfWork,
        usuario_id: int,
        data: AsignacionCrear,
        actor: Usuario,
    ) -> AsignacionOut:
        async with uow:
            await self._exigir_usuario(uow, usuario_id)
            momento = ahora()
            abierta = await uow.asignaciones.get_abierta(usuario_id, data.rol)
            if abierta:
                if abierta.vence_en is None or abierta.vence_en > momento:
                    raise ErrorConflicto("El usuario ya tiene ese rol asignado")
                abierta.revocada_en = momento
                await uow.asignaciones.update(abierta)
            asignacion = AsignacionRol(
                usuario_id=usuario_id,
                rol=data.rol,
                desde=momento,
                vence_en=data.vence_en,
                otorgada_por=actor.id,
            )
            await uow.asignaciones.add(asignacion)
            await uow.eventos.add(
                EventoSeguridad(
                    actor=actor.email,
                    accion=f"Asignar {data.rol} al usuario {usuario_id}",
                )
            )
            return self._asignacion_out(asignacion, momento)

    async def revocar_rol(
        self, uow: UsuarioUnitOfWork, usuario_id: int, rol: str, actor: Usuario
    ) -> AsignacionOut:
        async with uow:
            await self._exigir_usuario(uow, usuario_id)
            asignacion = await uow.asignaciones.get_abierta(usuario_id, rol)
            if asignacion is None:
                raise ErrorNoEncontrado("No existe una asignación abierta de ese rol")
            momento = ahora()
            if rol == Rol.ADMIN:
                if usuario_id == actor.id:
                    raise ErrorConflicto("No puede revocarse su propio rol ADMIN")
                if await uow.asignaciones.contar_administradores(momento) <= 1:
                    raise ErrorConflicto(
                        "Debe quedar al menos un administrador vigente"
                    )
            asignacion.revocada_en = momento
            await uow.asignaciones.update(asignacion)
            await uow.eventos.add(
                EventoSeguridad(
                    actor=actor.email, accion=f"Revocar {rol} al usuario {usuario_id}"
                )
            )
            return self._asignacion_out(asignacion, momento)

    async def cambiar_password(
        self, uow: UsuarioUnitOfWork, usuario: Usuario, data: CambiarPasswordIn
    ) -> list[str]:
        if not await verificar_password(data.password_actual, usuario.password_hash):
            raise ErrorNoAutenticado("La contraseña actual es incorrecta")
        password_hash = await hash_password(data.password_nueva)
        async with uow:
            usuario.password_hash = password_hash
            usuario.password_cambiada_en = ahora()
            usuario.debe_cambiar_password = False
            await uow.usuarios.update(usuario)
            await uow.eventos.add(
                EventoSeguridad(actor=usuario.email, accion="Cambio de contraseña")
            )
            return await uow.asignaciones.get_vigentes_de_usuario(usuario.id, ahora())

    async def eventos(
        self, uow: UsuarioUnitOfWork, params: ParametrosPagina
    ) -> Pagina[EventoOut]:
        async with uow:
            total = await uow.eventos.count()
            page, size, pages = calcular_paginacion(total, params)
            filas = await uow.eventos.get_paginado(page, size)
            return Pagina[EventoOut](
                items=[EventoOut.model_validate(fila) for fila in filas],
                total=total,
                page=page,
                size=size,
                pages=pages,
            )
