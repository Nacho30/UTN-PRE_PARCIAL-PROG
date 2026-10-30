"""Servicios de autenticación (`ServiceAuth`) y administración de usuarios (`UsuariosService`).

Respeta la separación estricta de capas:
- Recibe `UsuarioUnitOfWork` (y `AccesoUnitOfWork` en el login) inyectados desde el router
  y los abre con `async with`; nunca construye un Unit of Work ni ejecuta SQL directo.
"""

from datetime import UTC, datetime, timedelta
import math

from fastapi import Request, Response

from app.core.config import Settings, get_settings
from app.core.errores import (
    ErrorConflicto,
    ErrorDemasiadosIntentos,
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
    LoginOut,
    LogoutOut,
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
        """Auto-registro atómico de cliente (RN-02).

        1. Calcula el hash bcrypt ANTES de abrir la transacción para no retener una conexión
           del pool mientras corre el cálculo intensivo en CPU.
        2. Dentro de un único bloque `async with uow:`, crea `Usuario`, `AsignacionRol(CLIENTE)`,
           `Cliente` y `EventoSeguridad` mediante sus repositorios. Si el correo o el documento
           ya existen, el `IntegrityError` en el `flush()` revierte todas las escrituras y se
           traduce a 409.
        """
        settings = settings or get_settings()
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
                usuario_id=usuario.id,  # type: ignore[arg-type]
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
                id=usuario.id,  # type: ignore[arg-type]
                email=usuario.email,
                nombre=usuario.nombre,
                roles=[Rol.CLIENTE],
                activo=usuario.activo,
                debe_cambiar_password=usuario.debe_cambiar_password,
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
        ahora_dt: datetime | None = None,
    ) -> LoginOut:
        """Inicia sesión respetando el orden obligatorio de seguridad (RN-08, RN-09).

        1. Límite de intentos en `AccesoUnitOfWork` (sobre la ventana de 60 s):
           si hay 5 fallos vigentes desde el último éxito, responde 429 con `Retry-After`
           SIN calcular ningún hash bcrypt y sin anotar el intento bloqueado.
        2. Lectura corta del usuario y sus roles vigentes en `UsuarioUnitOfWork`.
        3. Verificación con bcrypt en `to_thread` + semáforo, SIN transacción abierta,
           contra el hash del usuario o contra `hash_ficticio` si no existe o está inactivo.
        4. Registro del intento en `AccesoUnitOfWork` (sesión y transacción propias).
        5. Si falla, responde 401 «Correo o contraseña incorrectos» (indistinguible).
        6. Si acierta, emite el JWT con `sub`, `iat` float, `exp` y `roles` vigentes en cookie.
        """
        settings = settings or get_settings()
        momento = ahora_dt or datetime.now(UTC)
        ip = request.client.host if request.client else "0.0.0.0"

        # 1. Límite de intentos (RN-08), lo primero y sin calcular ningún hash. Cuesta UNA
        #    consulta: los fallos de (email, ip) dentro de la ventana y posteriores al último
        #    éxito, del más nuevo al más viejo, con LIMIT LOGIN_MAX_FALLOS. Si hay tantos como
        #    el máximo, el último de la lista es el que tiene que salir de la ventana.
        async with acceso:
            fallos = await acceso.intentos.get_fallos_recientes(
                data.email,
                ip,
                settings.LOGIN_VENTANA_SEGUNDOS,
                limite=settings.LOGIN_MAX_FALLOS,
                ahora=momento,
            )
        if len(fallos) >= settings.LOGIN_MAX_FALLOS:
            mas_viejo = fallos[-1].cuando
            if mas_viejo.tzinfo is None:
                mas_viejo = mas_viejo.replace(tzinfo=UTC)
            ahora_utc = momento if momento.tzinfo is not None else momento.replace(tzinfo=UTC)
            libera_en = mas_viejo + timedelta(seconds=settings.LOGIN_VENTANA_SEGUNDOS)
            retry_after = max(1, math.ceil((libera_en - ahora_utc).total_seconds()))
            raise ErrorDemasiadosIntentos(retry_after=retry_after)

        # 2. UoW de la petición: leer el usuario por email y sus roles vigentes
        usuario: Usuario | None = None
        roles_vigentes: list[str] = []
        async with uow:
            usuario = await uow.usuarios.get_by_email(data.email)
            if usuario is not None and usuario.id is not None:
                roles_vigentes = await uow.asignaciones.get_vigentes_de_usuario(
                    usuario.id, momento
                )

        # 3. bcrypt.checkpw en to_thread + semáforo, SIN transacción abierta (RN-09)
        hash_a_verificar = (
            usuario.password_hash
            if (usuario is not None and usuario.activo)
            else app_state.hash_ficticio
        )
        verificado = await verificar_password(data.password, hash_a_verificar)
        exito = bool(verificado and usuario is not None and usuario.activo)

        # 4. Anotar el intento en su propia sesión y transacción (Ejercicio 7, sección 6.8.1).
        # Razón: si se usara la sesión de la petición principal, al lanzar el 401 en el paso 5
        # la transacción se revertiría (rollback) y el intento fallido se perdería, impidiendo
        # contar los 5 fallos de RN-08.
        # Costo: consume una sesión separada y confirma una escritura en `intento_acceso` en
        # cada login, dejando filas persistidas incluso cuando la petición falla con 401.
        async with acceso:
            intento = IntentoAcceso(
                email=data.email,
                ip=ip,
                exito=exito,
                cuando=momento,
            )
            await acceso.intentos.add(intento)

        # 5. Si las credenciales no son válidas, responder 401 indistinguible
        if not exito or usuario is None:
            raise ErrorNoAutenticado("Correo o contraseña incorrectos")

        # 6. Roles vigentes → JWT → Set-Cookie y contrato de salida sin token
        token = crear_token(sub=usuario.email, roles=roles_vigentes, settings=settings)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            secure=settings.COOKIE_SECURE,
            max_age=settings.jwt_expira_segundos,
        )
        return LoginOut(
            mensaje="Sesión iniciada",
            debe_cambiar_password=usuario.debe_cambiar_password,
            expira_en_segundos=settings.jwt_expira_segundos,
        )

    @staticmethod
    async def logout(response: Response) -> LogoutOut:
        response.delete_cookie(key="access_token", httponly=True, samesite="lax")
        return LogoutOut()


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
