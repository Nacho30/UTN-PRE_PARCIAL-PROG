import pytest
from pydantic import TypeAdapter, ValidationError

from app.core.tipos import (
    Documento,
    EmailNormalizado,
    PasswordBcrypt,
    Telefono,
    TextoCorto,
)
from app.modules.usuarios.schemas import (
    LoginIn,
    LoginOut,
    RegistroIn,
    UsuarioOut,
    YoOut,
)


def test_password_bcrypt_72_bytes():
    ta = TypeAdapter(PasswordBcrypt)
    assert ta.validate_python("contraseña123") == "contraseña123"
    # Exactamente 72 bytes ASCII pasa
    assert ta.validate_python("a" * 72) == "a" * 72
    # 36 «ñ» son exactamente 72 bytes en UTF-8 -> pasa
    assert ta.validate_python("ñ" * 36) == "ñ" * 36
    # 37 «ñ» son 74 bytes en UTF-8 -> falla
    with pytest.raises(ValidationError):
        ta.validate_python("ñ" * 37)
    # 73 bytes ASCII falla
    with pytest.raises(ValidationError):
        ta.validate_python("a" * 73)
    # 40 «ñ» son 80 bytes en UTF-8 -> debe fallar (422 en endpoint)
    with pytest.raises(ValidationError):
        ta.validate_python("ñ" * 40)


def test_contratos_schemas_auth():
    # RegistroIn normaliza email y exige documento
    reg = RegistroIn(
        email="  Nuevo.Cliente@Taller.COM  ",
        nombre="  Juan Pérez  ",
        password="Password123!",
        documento="33444555",
        telefono="1155556666",
    )
    assert reg.email == "nuevo.cliente@taller.com"
    assert reg.nombre == "Juan Pérez"
    assert reg.documento == "33444555"
    assert reg.telefono == "1155556666"

    # Sin documento debe fallar
    with pytest.raises(ValidationError):
        RegistroIn(
            email="test@taller.com",
            nombre="Juan",
            password="Password123!",
        )  # type: ignore[call-arg]

    # Contraseña de 40 «ñ» en RegistroIn y LoginIn debe fallar
    with pytest.raises(ValidationError):
        RegistroIn(
            email="test@taller.com",
            nombre="Juan",
            password="ñ" * 40,
            documento="33444555",
            telefono="1155556666",
        )

    with pytest.raises(ValidationError):
        LoginIn(email="test@taller.com", password="ñ" * 40)

    # Campos no declarados rechazados (extra="forbid") y caracter nulo rechazado
    with pytest.raises(ValidationError):
        RegistroIn(
            email="test@taller.com",
            nombre="Juan",
            password="Password123!",
            documento="33444555",
            rol="ADMIN",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        RegistroIn(
            email="test@taller.com",
            nombre="Juan\x00",
            password="Password123!",
            documento="33444555",
        )

    # LoginOut no incluye token y tiene los campos de la consigna
    login_out = LoginOut(debe_cambiar_password=False, expira_en_segundos=1800)
    dumped_login = login_out.model_dump()
    assert dumped_login == {
        "mensaje": "Sesión iniciada",
        "debe_cambiar_password": False,
        "expira_en_segundos": 1800,
    }
    assert "token" not in dumped_login
    assert "access_token" not in dumped_login

    # YoOut expone roles_vigentes y roles_token, nunca password_hash
    yo = YoOut(
        id=1,
        email="cliente@example.com",
        nombre="Laura Cliente",
        activo=True,
        debe_cambiar_password=False,
        roles=["CLIENTE"],
        roles_vigentes=["CLIENTE"],
        roles_token=["CLIENTE", "RECEPCION"],
    )
    dumped_yo = yo.model_dump()
    assert dumped_yo["roles_vigentes"] == ["CLIENTE"]
    assert dumped_yo["roles_token"] == ["CLIENTE", "RECEPCION"]
    assert "password_hash" not in dumped_yo


def _run(coro):
    """Ejecuta una corrutina sin crear sockets del bucle de Windows cuando todas las esperas son en memoria."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


class AsyncSessionSqliteAdapter:
    """Adaptador asincrónico sobre SQLAlchemy Session (SQLite) para tests aislados y deterministas."""

    def __init__(self, sync_session) -> None:
        self._sync = sync_session

    def add(self, instance: object) -> None:
        self._sync.add(instance)

    def add_all(self, instances: object) -> None:
        self._sync.add_all(instances)

    async def execute(self, statement, *args, **kwargs):
        return self._sync.execute(statement, *args, **kwargs)

    async def flush(self) -> None:
        self._sync.flush()

    async def commit(self) -> None:
        self._sync.commit()

    async def rollback(self) -> None:
        self._sync.rollback()

    async def delete(self, instance: object) -> None:
        self._sync.delete(instance)

    async def close(self) -> None:
        self._sync.close()

    def in_transaction(self) -> bool:
        return self._sync.in_transaction()

    def begin(self):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _tx():
            try:
                yield self
            except Exception:
                self._sync.rollback()
                raise
            else:
                self._sync.commit()

        return _tx()

    async def __aenter__(self) -> "AsyncSessionSqliteAdapter":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._sync.close()


def _crear_db_factory(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import SQLModel
    import app.modelos  # noqa: F401

    db_file = tmp_path / "taller_test.db"
    engine = create_engine(f"sqlite:///{db_file}")
    SQLModel.metadata.create_all(engine)
    sync_maker = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def factory():
        return AsyncSessionSqliteAdapter(sync_maker())

    return factory


def test_repositorios_y_uow(tmp_path):
    from datetime import UTC, datetime, timedelta
    from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Rol, Usuario
    from app.modules.usuarios.unit_of_work import AccesoUnitOfWork, UsuarioUnitOfWork

    session_factory = _crear_db_factory(tmp_path)
    ahora = datetime.now(UTC)

    async def escenario():
        session = session_factory()
        uow = UsuarioUnitOfWork(session)
        # UsuarioUnitOfWork debe componer usuarios, asignaciones y clientes en la misma sesión
        assert hasattr(uow, "usuarios")
        assert hasattr(uow, "asignaciones")
        assert hasattr(uow, "clientes")
        assert uow.usuarios.session is session
        assert uow.asignaciones.session is session
        assert uow.clientes.session is session

        async with uow:
            u = Usuario(email="ana@taller.com", nombre="Ana", password_hash="hash")
            await uow.usuarios.add(u)
            assert u.id is not None

            # 1 rol vigente sin vencimiento, 1 vigente con vencimiento futuro, 1 vencido, 1 revocado
            await uow.asignaciones.add(AsignacionRol(usuario_id=u.id, rol=Rol.CLIENTE))
            await uow.asignaciones.add(
                AsignacionRol(
                    usuario_id=u.id,
                    rol=Rol.RECEPCION,
                    vence_en=ahora + timedelta(days=1),
                )
            )
            await uow.asignaciones.add(
                AsignacionRol(
                    usuario_id=u.id,
                    rol=Rol.MECANICO,
                    vence_en=ahora - timedelta(seconds=10),
                )
            )
            await uow.asignaciones.add(
                AsignacionRol(
                    usuario_id=u.id,
                    rol=Rol.ADMIN,
                    revocada_en=ahora - timedelta(minutes=5),
                )
            )

            roles = await uow.asignaciones.get_roles_vigentes(u.id, ahora=ahora)
            assert set(roles) == {Rol.CLIENTE, Rol.RECEPCION}
        await session.close()

        # Probar IntentoAccesoRepository con ventana de 60s y reinicio tras éxito
        acceso_uow = AccesoUnitOfWork(session_factory)
        async with acceso_uow:
            # 2 fallos viejos (hace 120s, fuera de la ventana de 60s)
            for i in range(2):
                await acceso_uow.intentos.add(
                    IntentoAcceso(
                        email="ana@taller.com",
                        ip="127.0.0.1",
                        exito=False,
                        cuando=ahora - timedelta(seconds=120 - i),
                    )
                )
            # 4 fallos recientes dentro de la ventana de 60s
            for i in range(4):
                await acceso_uow.intentos.add(
                    IntentoAcceso(
                        email="ana@taller.com",
                        ip="127.0.0.1",
                        exito=False,
                        cuando=ahora - timedelta(seconds=40 - i),
                    )
                )

        async with acceso_uow:
            # Los 2 viejos no deben contarse -> solo 4 en la ventana de 60s
            conteo = await acceso_uow.intentos.contar_fallos_recientes(
                "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
            )
            assert conteo == 4
            assert (
                await acceso_uow.intentos.get_quinto_fallo(
                    "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
                )
                is None
            )

            # Agregamos el 5to fallo dentro de la ventana (hace 10s)
            await acceso_uow.intentos.add(
                IntentoAcceso(
                    email="ana@taller.com",
                    ip="127.0.0.1",
                    exito=False,
                    cuando=ahora - timedelta(seconds=10),
                )
            )
            conteo5 = await acceso_uow.intentos.contar_fallos_recientes(
                "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
            )
            assert conteo5 == 5
            quinto = await acceso_uow.intentos.get_quinto_fallo(
                "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
            )
            assert quinto is not None

            # Un login exitoso reinicia la cuenta
            await acceso_uow.intentos.add(
                IntentoAcceso(
                    email="ana@taller.com",
                    ip="127.0.0.1",
                    exito=True,
                    cuando=ahora - timedelta(seconds=5),
                )
            )
            conteo_post_exito = await acceso_uow.intentos.contar_fallos_recientes(
                "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
            )
            assert conteo_post_exito == 0

            # Fallos de otra IP no afectan a (ana@taller.com, 127.0.0.1)
            await acceso_uow.intentos.add(
                IntentoAcceso(
                    email="ana@taller.com",
                    ip="10.0.0.99",
                    exito=False,
                    cuando=ahora - timedelta(seconds=1),
                )
            )
            assert (
                await acceso_uow.intentos.contar_fallos_recientes(
                    "ana@taller.com", "127.0.0.1", ventana_segundos=60, ahora=ahora
                )
                == 0
            )
            assert (
                await acceso_uow.intentos.contar_fallos_recientes(
                    "ana@taller.com", "10.0.0.99", ventana_segundos=60, ahora=ahora
                )
                == 1
            )

    _run(escenario())


def _preparar_app_test(tmp_path, monkeypatch):
    import asyncio
    import anyio.to_thread
    import fastapi.dependencies.utils
    from main import app
    from app.core.database import get_session
    from app.core.security import _hash_sync

    # En el entorno de test ejecutamos to_thread de forma inmediata para no abrir sockets de bucle Windows
    async def _immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    async def _immediate_run_sync(func, *args, abandon_on_cancel=False, limiter=None):
        return func(*args)

    async def _immediate_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _immediate_to_thread)
    monkeypatch.setattr(anyio.to_thread, "run_sync", _immediate_run_sync)
    monkeypatch.setattr(fastapi.dependencies.utils, "run_in_threadpool", _immediate_run_in_threadpool)

    session_factory = _crear_db_factory(tmp_path)
    app.state.session_factory = session_factory
    app.state.hash_ficticio = _hash_sync("ficticio_test_secret", 4)

    async def _override_get_session():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_session] = _override_get_session
    return app, session_factory


def test_endpoints_registro_atomico_y_72_bytes(tmp_path, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from app.modules.clientes.models import Cliente
    from app.modules.usuarios.models import AsignacionRol, Usuario

    app, session_factory = _preparar_app_test(tmp_path, monkeypatch)

    async def escenario():
        # Pre-cargamos a Jorge (cliente del taller sin usuario, documento="28999888")
        async with session_factory() as s:
            jorge = Cliente(
                usuario_id=None,
                nombre="Jorge Pérez",
                documento="28999888",
                telefono="1166667777",
            )
            s.add(jorge)
            await s.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Contraseña de 40 «ñ» (80 bytes UTF-8) -> 422
            res_72 = await ac.post(
                "/auth/registro",
                json={
                    "email": "larga@taller.com",
                    "nombre": "Clave Larga",
                    "password": "ñ" * 40,
                    "documento": "40111222",
                    "telefono": "1100001111",
                },
            )
            assert res_72.status_code == 422

            # 2. Auto-registro válido -> 201 y crea Usuario + AsignacionRol(CLIENTE) + Cliente
            res_ok = await ac.post(
                "/auth/registro",
                json={
                    "email": "laura@taller.com",
                    "nombre": "Laura Cliente",
                    "password": "Password123!",
                    "documento": "30111222",
                    "telefono": "1144445555",
                },
            )
            assert res_ok.status_code == 201
            body_ok = res_ok.json()
            assert body_ok["email"] == "laura@taller.com"
            assert "CLIENTE" in body_ok["roles"]
            assert "password_hash" not in body_ok

            # 3. Correo repetido -> 409 «El correo ya está registrado»
            res_dup_email = await ac.post(
                "/auth/registro",
                json={
                    "email": "LAURA@taller.com",
                    "nombre": "Otra Laura",
                    "password": "Password123!",
                    "documento": "99888777",
                    "telefono": "1144445555",
                },
            )
            assert res_dup_email.status_code == 409
            assert res_dup_email.json()["detail"] == "El correo ya está registrado"

            # 4. Documento de cliente ya existente (Jorge, "28999888") -> 409 y rollback total (RN-02)
            res_dup_doc = await ac.post(
                "/auth/registro",
                json={
                    "email": "impostor@taller.com",
                    "nombre": "Impostor",
                    "password": "Password123!",
                    "documento": "28999888",
                    "telefono": "1199990000",
                },
            )
            assert res_dup_doc.status_code == 409
            assert "documento" in res_dup_doc.json()["detail"].lower()

            # Verificar en la base que impostor@taller.com NO quedó creado ni su rol, y Jorge sigue sin usuario
            async with session_factory() as s:
                u_imp = (
                    await s.execute(select(Usuario).where(Usuario.email == "impostor@taller.com"))
                ).scalars().first()
                assert u_imp is None

                roles_all = (await s.execute(select(AsignacionRol))).scalars().all()
                assert len(roles_all) == 1  # solo el de Laura

                jorge_db = (
                    await s.execute(select(Cliente).where(Cliente.documento == "28999888"))
                ).scalars().first()
                assert jorge_db is not None
                assert jorge_db.usuario_id is None

    try:
        _run(escenario())
    finally:
        app.dependency_overrides.clear()


def test_endpoints_login_rate_limit_yo_y_logout(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    from app.modules.usuarios.models import AsignacionRol, IntentoAcceso, Rol, Usuario

    app, session_factory = _preparar_app_test(tmp_path, monkeypatch)

    async def escenario():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Registrar un usuario válido
            res_reg = await ac.post(
                "/auth/registro",
                json={
                    "email": "cliente@example.com",
                    "nombre": "Laura Cliente",
                    "password": "Cliente1234!",
                    "documento": "30111222",
                    "telefono": "1144445555",
                },
            )
            assert res_reg.status_code == 201
            usuario_id = res_reg.json()["id"]

            # 1. Login con correo inexistente vs contraseña incorrecta -> 401 mismo mensaje (RN-09)
            res_no_existe = await ac.post(
                "/auth/login",
                json={"email": "noexiste@example.com", "password": "PasswordMala1!"},
            )
            assert res_no_existe.status_code == 401
            assert res_no_existe.json() == {"detail": "Correo o contraseña incorrectos"}

            # Limpiamos intentos previos y probamos que fallos fuera de la ventana (>60s) NO bloquean
            ahora = datetime.now(UTC)
            async with session_factory() as s:
                for i in range(5):
                    s.add(
                        IntentoAcceso(
                            email="cliente@example.com",
                            ip="127.0.0.1",
                            exito=False,
                            cuando=ahora - timedelta(seconds=90 + i),
                        )
                    )
                await s.commit()

            # 2. 6 intentos fallidos seguidos en la ventana de 60s:
            # Los primeros 5 responden 401 (no se bloquean por los 5 viejos de hace >90s)
            for _ in range(5):
                res_fail = await ac.post(
                    "/auth/login",
                    json={"email": "cliente@example.com", "password": "PasswordMala1!"},
                )
                assert res_fail.status_code == 401
                assert res_fail.json() == {"detail": "Correo o contraseña incorrectos"}

            # El 6to intento seguido dentro de los 60s responde 429 con Retry-After y NO agrega un 6to fallo reciente
            res_429 = await ac.post(
                "/auth/login",
                json={"email": "cliente@example.com", "password": "PasswordMala1!"},
            )
            assert res_429.status_code == 429
            assert "Retry-After" in res_429.headers
            assert int(res_429.headers["Retry-After"]) >= 1

            async with session_factory() as s:
                intentos_recientes = (
                    await s.execute(
                        select(IntentoAcceso).where(
                            IntentoAcceso.email == "cliente@example.com",
                            IntentoAcceso.cuando >= ahora - timedelta(seconds=5),
                        )
                    )
                ).scalars().all()
                assert len(intentos_recientes) == 5

                # Movemos esos 5 intentos fuera de la ventana (>60s) para poder iniciar sesión
                for it in intentos_recientes:
                    it.cuando = ahora - timedelta(seconds=120)
                await s.commit()

            # 3. Login correcto -> 200 con LoginOut sin token y Set-Cookie HttpOnly, SameSite=lax, Max-Age
            res_login = await ac.post(
                "/auth/login",
                json={"email": "cliente@example.com", "password": "Cliente1234!"},
            )
            assert res_login.status_code == 200
            body_login = res_login.json()
            assert body_login == {
                "mensaje": "Sesión iniciada",
                "debe_cambiar_password": False,
                "expira_en_segundos": 1800,
            }
            assert "token" not in body_login
            assert "access_token" not in body_login

            set_cookie = res_login.headers.get("set-cookie", "")
            assert "access_token=" in set_cookie
            assert "httponly" in set_cookie.lower()
            assert "samesite=lax" in set_cookie.lower()
            assert "max-age=1800" in set_cookie.lower()
            token = res_login.cookies.get("access_token")
            assert token is not None

            # 4. GET /auth/yo con cookie válida -> 200 con roles_vigentes y roles_token
            res_yo = await ac.get("/auth/yo")
            assert res_yo.status_code == 200
            body_yo = res_yo.json()
            assert body_yo["email"] == "cliente@example.com"
            assert body_yo["roles_vigentes"] == ["CLIENTE"]
            assert body_yo["roles_token"] == ["CLIENTE"]
            assert "password_hash" not in body_yo

            # Si se revoca el rol en la base con la sesión abierta, /auth/yo muestra la diferencia
            async with session_factory() as s:
                asig = (
                    await s.execute(
                        select(AsignacionRol).where(AsignacionRol.usuario_id == usuario_id)
                    )
                ).scalars().first()
                assert asig is not None
                asig.revocada_en = datetime.now(UTC)
                await s.commit()

            res_yo_diff = await ac.get("/auth/yo")
            assert res_yo_diff.status_code == 200
            assert res_yo_diff.json()["roles_vigentes"] == []
            assert res_yo_diff.json()["roles_token"] == ["CLIENTE"]

            # 5. GET /auth/yo sin cookie pero con Authorization: Bearer <token> -> 401
            ac.cookies.clear()
            res_bearer = await ac.get(
                "/auth/yo",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_bearer.status_code == 401

            # 6. RN-07: si password_cambiada_en es posterior (incluso en el mismo segundo) a iat -> 401
            ac.cookies.set("access_token", token)
            async with session_factory() as s:
                u_db = (
                    await s.execute(select(Usuario).where(Usuario.id == usuario_id))
                ).scalars().first()
                assert u_db is not None
                u_db.password_cambiada_en = datetime.now(UTC) + timedelta(milliseconds=10)
                await s.commit()

            res_rn07 = await ac.get("/auth/yo")
            assert res_rn07.status_code == 401

            # 7. POST /auth/logout -> 200 y borra la cookie
            res_logout = await ac.post("/auth/logout")
            assert res_logout.status_code == 200
            assert 'access_token=""' in res_logout.headers.get("set-cookie", "") or "max-age=0" in res_logout.headers.get("set-cookie", "").lower()

    try:
        _run(escenario())
    finally:
        app.dependency_overrides.clear()


def test_triangulacion_seguridad_y_capas(tmp_path, monkeypatch):
    import inspect
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select
    import app.modules.usuarios.router as router_mod
    import app.modules.usuarios.service as service_mod
    from app.modules.usuarios.models import Usuario

    # Verificación estática de separación de capas (AGENTS.md):
    # Ni el servicio ni el router ejecutan select(...) ni session.add(...), y el servicio no instancia UoW.
    src_service = inspect.getsource(service_mod)
    src_router = inspect.getsource(router_mod)
    assert "select(" not in src_service
    assert "session.add(" not in src_service
    assert "UsuarioUnitOfWork(" not in src_service
    assert "AccesoUnitOfWork(" not in src_service
    assert "select(" not in src_router
    assert "session.add(" not in src_router

    app, session_factory = _preparar_app_test(tmp_path, monkeypatch)

    # Espía sobre verificar_password para comprobar RN-08 (no hashea en 429) y RN-09 (usa hash_ficticio)
    llamadas_verificar: list[tuple[str, str]] = []
    orig_verificar = service_mod.verificar_password

    async def _spy_verificar(password: str, password_hash: str) -> bool:
        llamadas_verificar.append((password, password_hash))
        return await orig_verificar(password, password_hash)

    monkeypatch.setattr(service_mod, "verificar_password", _spy_verificar)

    async def escenario():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login de correo inexistente verifica contra hash_ficticio (RN-09)
            res_fantasma = await ac.post(
                "/auth/login",
                json={"email": "fantasma@taller.com", "password": "Password123!"},
            )
            assert res_fantasma.status_code == 401
            assert len(llamadas_verificar) == 1
            assert llamadas_verificar[0][1] == app.state.hash_ficticio

            # Completamos 5 fallos para fantasma@taller.com
            for _ in range(4):
                await ac.post(
                    "/auth/login",
                    json={"email": "fantasma@taller.com", "password": "Password123!"},
                )
            assert len(llamadas_verificar) == 5

            # El 6to intento responde 429 SIN llamar a verificar_password (RN-08)
            res_bloqueado = await ac.post(
                "/auth/login",
                json={"email": "fantasma@taller.com", "password": "Password123!"},
            )
            assert res_bloqueado.status_code == 429
            assert len(llamadas_verificar) == 5  # no aumentó

            # 2. Usuario inactivo: no puede iniciar sesión ni usar /auth/yo
            await ac.post(
                "/auth/registro",
                json={
                    "email": "inactivo@taller.com",
                    "nombre": "Usuario Inactivo",
                    "password": "Password123!",
                    "documento": "55666777",
                    "telefono": "1122223333",
                },
            )
            res_login_ok = await ac.post(
                "/auth/login",
                json={"email": "inactivo@taller.com", "password": "Password123!"},
            )
            assert res_login_ok.status_code == 200

            # Desactivamos al usuario en la base
            async with session_factory() as s:
                u_db = (
                    await s.execute(select(Usuario).where(Usuario.email == "inactivo@taller.com"))
                ).scalars().first()
                assert u_db is not None
                u_db.activo = False
                await s.commit()

            # Con cookie de sesión abierta pero usuario inactivo -> /auth/yo da 401
            res_yo_inactivo = await ac.get("/auth/yo")
            assert res_yo_inactivo.status_code == 401

            # Y el login con contraseña correcta pero usuario inactivo -> 401
            res_login_inactivo = await ac.post(
                "/auth/login",
                json={"email": "inactivo@taller.com", "password": "Password123!"},
            )
            assert res_login_inactivo.status_code == 401

            # 3. Cookie adulterada -> 401
            ac.cookies.set("access_token", "token.invalido.adulterado")
            res_yo_invalido = await ac.get("/auth/yo")
            assert res_yo_invalido.status_code == 401

    try:
        _run(escenario())
    finally:
        app.dependency_overrides.clear()


