"""Servicio de autenticación y usuarios (reglas de negocio).

Respeta la separación estricta de capas:
- Recibe `UsuarioUnitOfWork` (y `AccesoUnitOfWork` en el login) inyectados desde el router
  y los abre con `async with`; nunca construye un Unit of Work ni ejecuta SQL directo.
- No depende de objetos HTTP (`Request` / `Response`) de FastAPI.
"""

from datetime import UTC, datetime, timedelta
import math

from app.core.config import Settings, get_settings
from app.core.errores import (
    ErrorDemasiadosIntentos,
    ErrorDominio,
    ErrorNoAutenticado,
)
from app.core.security import crear_token, hash_password, verificar_password
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Rol, Usuario
from app.modules.usuarios.schemas import (
    LoginIn,
    LoginOut,
    RegistroIn,
    UsuarioOut,
    YoOut,
)
from app.modules.usuarios.unit_of_work import AccesoUnitOfWork, UsuarioUnitOfWork


class AuthError(ErrorDominio):
    pass


class UsuariosService:
    async def registrar_usuario(
        self,
        uow: UsuarioUnitOfWork,
        data: RegistroIn,
        settings: Settings | None = None,
    ) -> UsuarioOut:
        """Auto-registro atómico de cliente (RN-02).

        1. Calcula el hash bcrypt ANTES de abrir la transacción para no retener una conexión
           del pool mientras corre el cálculo intensivo en CPU.
        2. Dentro de un único bloque `async with uow:`, crea `Usuario`, `AsignacionRol(CLIENTE)`
           y `Cliente` mediante sus repositorios. Si el correo o el documento ya existen, el
           `IntegrityError` en el `flush()` revierte las tres escrituras y se traduce a 409.
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

            asignacion = AsignacionRol(
                usuario_id=usuario.id,  # type: ignore[arg-type]
                rol=Rol.CLIENTE,
            )
            await uow.asignaciones.add(asignacion)

            cliente = Cliente(
                usuario_id=usuario.id,
                nombre=data.nombre,
                documento=data.documento,
                telefono=data.telefono,
            )
            await uow.clientes.add(cliente)

            return UsuarioOut(
                id=usuario.id,  # type: ignore[arg-type]
                email=usuario.email,
                nombre=usuario.nombre,
                roles=[Rol.CLIENTE],
                activo=usuario.activo,
                debe_cambiar_password=usuario.debe_cambiar_password,
            )

    async def login(
        self,
        uow: UsuarioUnitOfWork,
        acceso_uow: AccesoUnitOfWork,
        data: LoginIn,
        ip: str,
        hash_ficticio: str,
        settings: Settings | None = None,
        ahora: datetime | None = None,
    ) -> tuple[str, LoginOut]:
        """Inicia sesión respetando el orden obligatorio de seguridad (RN-08, RN-09).

        1. Límite de intentos en `AccesoUnitOfWork` (1 consulta sobre la ventana de 60 s):
           si hay 5 fallos vigentes desde el último éxito, responde 429 con `Retry-After`
           SIN calcular ningún hash bcrypt y sin anotar el intento bloqueado.
        2. Lectura corta del usuario y sus roles vigentes en `UsuarioUnitOfWork`.
        3. Verificación con bcrypt en `to_thread` + semáforo, SIN transacción abierta,
           contra el hash del usuario o contra `hash_ficticio` si no existe o está inactivo.
        4. Registro del intento en `AccesoUnitOfWork` (sesión y transacción propias).
        5. Si falla, responde 401 «Correo o contraseña incorrectos» (indistinguible).
        6. Si acierta, emite el JWT con `sub`, `iat` float, `exp` y `roles` vigentes.
        """
        settings = settings or get_settings()
        momento = ahora or datetime.now(UTC)

        # 1. Controlar límite de intentos en la ventana configurada (RN-08)
        async with acceso_uow:
            fallos = await acceso_uow.intentos.get_fallos_recientes(
                email=data.email,
                ip=ip,
                ventana_segundos=settings.LOGIN_VENTANA_SEGUNDOS,
                limite=settings.LOGIN_MAX_FALLOS,
                ahora=momento,
            )
            if len(fallos) >= settings.LOGIN_MAX_FALLOS:
                quinto = fallos[settings.LOGIN_MAX_FALLOS - 1]
                cuando_utc = (
                    quinto.cuando
                    if quinto.cuando.tzinfo is not None
                    else quinto.cuando.replace(tzinfo=UTC)
                )
                ahora_utc = momento if momento.tzinfo is not None else momento.replace(tzinfo=UTC)
                delta = (cuando_utc + timedelta(seconds=settings.LOGIN_VENTANA_SEGUNDOS)) - ahora_utc
                retry_after = max(1, math.ceil(delta.total_seconds()))
                raise ErrorDemasiadosIntentos(retry_after=retry_after)

        # 2. Leer el usuario y sus roles vigentes en una transacción corta
        usuario: Usuario | None = None
        roles_vigentes: list[Rol] = []
        async with uow:
            usuario = await uow.usuarios.get_by_email(data.email)
            if usuario is not None and usuario.id is not None:
                roles_vigentes = await uow.asignaciones.get_roles_vigentes(
                    usuario.id,
                    ahora=momento,
                )

        # 3. Verificar contraseña fuera de toda transacción abierta (RN-09)
        hash_a_verificar = (
            usuario.password_hash
            if (usuario is not None and usuario.activo)
            else hash_ficticio
        )
        verificado = await verificar_password(data.password, hash_a_verificar)
        exito = bool(verificado and usuario is not None and usuario.activo)

        # 4. Anotar el intento en su propia sesión y transacción (Ejercicio 7, sección 6.8.1).
        # Razón: si se usara la sesión de la petición principal, al lanzar el 401 en el paso 5
        # la transacción se revertiría (rollback) y el intento fallido se perdería, impidiendo
        # contar los 5 fallos de RN-08.
        # Costo: consume una sesión separada y confirma una escritura en `intento_acceso` en
        # cada login, dejando filas persistidas incluso cuando la petición falla con 401.
        async with acceso_uow:
            intento = IntentoAcceso(
                email=data.email,
                ip=ip,
                exito=exito,
                cuando=momento,
            )
            await acceso_uow.intentos.add(intento)

        # 5. Si las credenciales no son válidas, responder 401 indistinguible
        if not exito or usuario is None:
            raise ErrorNoAutenticado("Correo o contraseña incorrectos")

        # 6. Emitir JWT con roles vigentes y devolver contrato de salida sin token
        roles_str = [str(r) for r in roles_vigentes]
        token = crear_token(sub=usuario.email, roles=roles_str, settings=settings)
        salida = LoginOut(
            mensaje="Sesión iniciada",
            debe_cambiar_password=usuario.debe_cambiar_password,
            expira_en_segundos=settings.jwt_expira_segundos,
        )
        return token, salida

    async def obtener_yo(
        self,
        uow: UsuarioUnitOfWork,
        usuario: Usuario,
        roles_token: list[str],
        ahora: datetime | None = None,
    ) -> YoOut:
        """Devuelve el usuario actual, sus roles vigentes en la base y los que trae el token."""
        async with uow:
            roles_vigentes = [
                str(r)
                for r in await uow.asignaciones.get_roles_vigentes(
                    usuario.id,  # type: ignore[arg-type]
                    ahora=ahora,
                )
            ]
        return YoOut(
            id=usuario.id,  # type: ignore[arg-type]
            email=usuario.email,
            nombre=usuario.nombre,
            activo=usuario.activo,
            debe_cambiar_password=usuario.debe_cambiar_password,
            roles=roles_vigentes,
            roles_vigentes=roles_vigentes,
            roles_token=[str(r) for r in roles_token],
        )


ServiceAuth = UsuariosService
