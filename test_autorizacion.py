"""Autorización con PostgreSQL real; todos los cambios se revierten al finalizar."""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.security import crear_token
from app.modules.usuarios.models import AsignacionRol, Usuario
from main import app
from seed import cargar
from test_auth import auth_client

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client(auth_client, monkeypatch):
    # El seed usa siete hashes concurrentes; cada prueba tiene su propio bucle.
    from app.core import security

    monkeypatch.setattr(security, "_semaforo", None)
    settings = get_settings()
    if settings.POSTGRES_PORT != 55432 or not settings.POSTGRES_DB.startswith(
        "parcial_"
    ):
        pytest.fail(
            "Estas pruebas requieren la base desechable parcial_* en el puerto 55432"
        )
    async with app.state.session_factory() as session:
        await cargar(session)
        await session.commit()
    return auth_client


def cookie(client, email="admin@example.com", roles=None):
    client.cookies.set("access_token", crear_token(email, roles or []))


@pytest.mark.parametrize(
    "path", ["/clientes/1", "/repuestos", "/ordenes", "/estados-orden"]
)
async def test_sin_cookie_responde_401(client, path):
    response = await client.get(path)
    assert response.status_code == 401


@pytest.mark.parametrize("token", ["invalido", crear_token("nadie@example.com", [])])
async def test_identidad_invalida(client, token):
    client.cookies.set("access_token", token)
    assert (await client.get("/auth/yo")).status_code == 401


async def test_bearer_no_reemplaza_cookie(client):
    response = await client.get(
        "/auth/yo",
        headers={"Authorization": f"Bearer {crear_token('admin@example.com', [])}"},
    )
    assert response.status_code == 401


async def test_usuario_inactivo(client):
    async with app.state.session_factory() as session:
        await session.execute(
            update(Usuario).where(Usuario.id == 1).values(activo=False)
        )
        await session.commit()
    cookie(client)
    assert (await client.get("/auth/yo")).status_code == 401


async def test_roles_token_no_autorizan(client):
    cookie(client, "cliente@example.com", ["ADMIN"])
    assert (await client.get("/repuestos")).status_code == 403


async def test_roles_base_autorizan_y_yo_distingue_token(client):
    cookie(client, "recepcion@example.com", ["CLIENTE"])
    assert (await client.get("/repuestos")).status_code == 200
    response = await client.get("/auth/yo")
    assert response.json()["roles_vigentes"] == ["RECEPCION"]
    assert response.json()["roles_token"] == ["CLIENTE"]


@pytest.mark.parametrize("cambio", ["revocada", "vencida", "futura"])
async def test_asignaciones_no_vigentes_no_autorizan(client, cambio):
    ahora = datetime.now(UTC)
    valores = {
        "revocada": {"revocada_en": ahora},
        "vencida": {"vence_en": ahora - timedelta(seconds=1)},
        "futura": {"desde": ahora + timedelta(days=1)},
    }[cambio]
    async with app.state.session_factory() as session:
        await session.execute(
            update(AsignacionRol).where(AsignacionRol.usuario_id == 3).values(**valores)
        )
        await session.commit()
    cookie(client, "recepcion@example.com", ["RECEPCION"])
    assert (await client.get("/repuestos")).status_code == 403


async def test_password_pendiente_no_bloquea_auth_ni_health(client):
    cookie(client, "nuevo@example.com", ["MECANICO"])
    assert (await client.get("/repuestos")).status_code == 403
    assert (await client.get("/auth/yo")).status_code == 200
    assert (await client.get("/health/live")).status_code == 200


@pytest.mark.parametrize("delta,esperado", [(-1, 401), (0, 200), (1, 200)])
async def test_iat_microsegundos_en_mismo_segundo(client, delta, esperado):
    import jwt

    momento = datetime.now(UTC).replace(microsecond=500000) - timedelta(seconds=2)
    async with app.state.session_factory() as session:
        await session.execute(
            update(Usuario).where(Usuario.id == 1).values(password_cambiada_en=momento)
        )
        await session.commit()
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iat": (momento + timedelta(microseconds=delta)).timestamp(),
            "exp": (momento + timedelta(minutes=30)).timestamp(),
            "roles": [],
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("access_token", token)
    assert (await client.get("/auth/yo")).status_code == esperado


@pytest.mark.parametrize(
    "momento",
    [datetime.now(UTC) - timedelta(seconds=1), datetime.now(UTC) - timedelta(days=1)],
)
async def test_token_vencido(client, momento):
    import jwt

    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "admin@example.com",
            "iat": momento.timestamp() - 100,
            "exp": momento.timestamp(),
            "roles": [],
        },
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("access_token", token)
    assert (await client.get("/auth/yo")).status_code == 401


async def test_alta_personal_y_evento(client):
    cookie(client)
    response = await client.post(
        "/usuarios",
        json={
            "email": "personal@example.com",
            "nombre": "Personal",
            "password": "Temporal123!",
            "roles": ["RECEPCION"],
        },
    )
    assert response.status_code == 201
    assert "password_hash" not in response.text
    cookie(client, "personal@example.com")
    assert (await client.get("/auth/yo")).json()["debe_cambiar_password"] is True
    assert (await client.get("/repuestos")).status_code == 403
    cookie(client)
    eventos = (await client.get("/eventos")).json()["items"]
    assert any(
        e["actor"] == "admin@example.com" and "personal@example.com" in e["accion"]
        for e in eventos
    )


@pytest.mark.parametrize("roles", [["CLIENTE"], [], ["ADMIN", "ADMIN"]])
async def test_alta_personal_rechaza_roles_invalidos(client, roles):
    cookie(client)
    response = await client.post(
        "/usuarios",
        json={
            "email": "personal@example.com",
            "nombre": "Personal",
            "password": "Temporal123!",
            "roles": roles,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("email", ["recepcion@example.com", "cliente@example.com"])
async def test_admin_endpoints_protegidos(client, email):
    cookie(client, email)
    for method, path, payload in [
        ("GET", "/usuarios/3/roles", None),
        ("POST", "/usuarios/3/roles", {"rol": "ADMIN"}),
        ("DELETE", "/usuarios/3/roles/RECEPCION", None),
        ("GET", "/eventos", None),
        (
            "POST",
            "/usuarios",
            {
                "email": "x@example.com",
                "nombre": "X",
                "password": "Temporal123!",
                "roles": ["ADMIN"],
            },
        ),
    ]:
        assert (await client.request(method, path, json=payload)).status_code == 403


async def test_revocar_sesion_abierta_conserva_historia(client):
    cookie(client, "recepcion@example.com", ["RECEPCION"])
    vieja = client.cookies.get("access_token")
    assert (await client.get("/repuestos")).status_code == 200
    cookie(client)
    assert (await client.delete("/usuarios/3/roles/RECEPCION")).status_code == 200
    historia = (await client.get("/usuarios/3/roles")).json()
    assert len(historia) == 1 and historia[0]["vigente"] is False
    assert historia[0]["revocada_en"] is not None
    client.cookies.set("access_token", vieja)
    assert (await client.get("/repuestos")).status_code == 403
    yo = (await client.get("/auth/yo")).json()
    assert yo["roles_vigentes"] == [] and yo["roles_token"] == ["RECEPCION"]


@pytest.mark.parametrize("vence", ["2030-01-01T00:00:00", "2000-01-01T00:00:00Z"])
async def test_vencimiento_invalido_422(client, vence):
    cookie(client)
    response = await client.post(
        "/usuarios/3/roles", json={"rol": "MECANICO", "vence_en": vence}
    )
    assert response.status_code == 422


async def test_reasignar_vencido_y_duplicado(client):
    async with app.state.session_factory() as session:
        await session.execute(
            update(AsignacionRol)
            .where(AsignacionRol.usuario_id == 3)
            .values(vence_en=datetime.now(UTC) - timedelta(days=1))
        )
        await session.commit()
    cookie(client)
    response = await client.post(
        "/usuarios/3/roles",
        json={"rol": "RECEPCION", "vence_en": "2030-01-01T00:00:00Z"},
    )
    assert response.status_code == 201
    historia = (await client.get("/usuarios/3/roles")).json()
    assert len(historia) == 2 and sum(h["vigente"] for h in historia) == 1
    assert historia[0]["revocada_en"] is not None
    assert (
        await client.post("/usuarios/3/roles", json={"rol": "RECEPCION"})
    ).status_code == 409


async def test_admin_no_se_revoca_y_no_quedan_cero_admins(client):
    cookie(client)
    assert (await client.delete("/usuarios/1/roles/ADMIN")).status_code == 409
    assert (await client.delete("/usuarios/2/roles/ADMIN")).status_code == 200
    # El administrador actor debe seguir vigente, por eso tampoco puede borrar el último propio.
    assert (await client.delete("/usuarios/1/roles/ADMIN")).status_code == 409


async def test_admin_inactivo_no_cuenta_para_proteccion(client):
    async with app.state.session_factory() as session:
        await session.execute(
            update(Usuario).where(Usuario.id == 2).values(activo=False)
        )
        await session.commit()
    cookie(client)
    # No se puede otorgar un vencimiento al último administrador sin otra asignación duradera.
    assert (await client.delete("/usuarios/1/roles/ADMIN")).status_code == 409


@pytest.mark.parametrize(
    "path,method",
    [
        ("/usuarios/999/roles", "GET"),
        ("/usuarios/999/roles", "POST"),
        ("/usuarios/999/roles/ADMIN", "DELETE"),
    ],
)
async def test_roles_usuario_inexistente_404(client, path, method):
    cookie(client)
    response = await client.request(
        method, path, json={"rol": "ADMIN"} if method == "POST" else None
    )
    assert response.status_code == 404


async def test_cambio_password_cookie_vieja_y_nueva(client):
    response = await client.post(
        "/auth/login",
        json={"email": "nuevo@example.com", "password": "Provisoria1234!"},
    )
    assert response.status_code == 200
    vieja = client.cookies.get("access_token")
    response = await client.post(
        "/auth/cambiar-password",
        json={"password_actual": "Provisoria1234!", "password_nueva": "Definitiva123!"},
    )
    assert response.status_code == 200
    nueva = response.cookies.get("access_token")
    assert nueva and nueva != vieja
    assert (await client.get("/repuestos")).status_code == 200
    client.cookies.set("access_token", vieja)
    assert (await client.get("/auth/yo")).status_code == 401
    client.cookies.set("access_token", nueva)
    assert (await client.get("/auth/yo")).json()["debe_cambiar_password"] is False


@pytest.mark.parametrize(
    "payload,esperado",
    [
        (
            {"password_actual": "Incorrecta123!", "password_nueva": "Definitiva123!"},
            401,
        ),
        ({"password_actual": "Provisoria1234!", "password_nueva": "ñ" * 37}, 422),
    ],
)
async def test_cambio_password_invalido(client, payload, esperado):
    cookie(client, "nuevo@example.com")
    assert (
        await client.post("/auth/cambiar-password", json=payload)
    ).status_code == esperado
    assert (await client.get("/auth/yo")).json()["debe_cambiar_password"] is True


async def test_eventos_paginados(client):
    cookie(client)
    response = await client.get("/eventos?size=1")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["actor"] == "SISTEMA"
    assert (await client.get("/eventos?page=2&size=1")).status_code == 422
    assert (await client.get("/eventos?size=101")).status_code == 422


async def test_login_emite_roles_vigentes(client):
    async with app.state.session_factory() as session:
        await session.execute(
            update(AsignacionRol)
            .where(AsignacionRol.usuario_id == 3)
            .values(vence_en=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()
    response = await client.post(
        "/auth/login",
        json={"email": "recepcion@example.com", "password": "Recepcion1234!"},
    )
    assert response.status_code == 200
    from app.core.security import decodificar_token

    assert decodificar_token(response.cookies.get("access_token"))["roles"] == []


@pytest.mark.parametrize(
    "email,esperado",
    [
        ("admin@example.com", 200),
        ("recepcion@example.com", 200),
        ("mecanico@example.com", 403),
        ("cliente@example.com", 403),
    ],
)
async def test_permiso_clientes(client, email, esperado):
    cookie(client, email)
    assert (await client.get("/clientes/1")).status_code == esperado


@pytest.mark.parametrize(
    "method,path,payload",
    [
        (
            "POST",
            "/repuestos",
            {
                "codigo": "NUEVO",
                "descripcion": "Nuevo",
                "precio": "100.00",
                "stock_inicial": 1,
            },
        ),
        ("PATCH", "/repuestos/1", {"descripcion": "Cambio"}),
        ("DELETE", "/repuestos/1", None),
        ("POST", "/repuestos/1/reponer", {"cantidad": 1, "motivo": "Prueba"}),
        ("GET", "/repuestos/1/movimientos", None),
        ("GET", "/repuestos/1/precios", None),
    ],
)
async def test_repuestos_admin_unicamente(client, method, path, payload):
    cookie(client, "recepcion@example.com")
    assert (await client.request(method, path, json=payload)).status_code == 403


async def test_lo_propio_no_requiere_rol_cliente(client):
    async with app.state.session_factory() as session:
        await session.execute(
            update(AsignacionRol)
            .where(AsignacionRol.usuario_id == 6)
            .values(revocada_en=datetime.now(UTC))
        )
        await session.commit()
    cookie(client, "cliente@example.com")
    vehiculos = await client.get("/mis-vehiculos")
    assert vehiculos.status_code == 200
    assert [v["id"] for v in vehiculos.json()] == [1, 2]
    ordenes = await client.get("/mis-ordenes?size=1")
    assert ordenes.status_code == 200
    assert ordenes.json()["total"] == 1 and ordenes.json()["items"][0]["id"] == 1
    assert (await client.get("/mis-ordenes?page=2&size=1")).status_code == 422
    assert (await client.get("/ordenes/1")).status_code == 200
    assert (await client.get("/ordenes/2")).status_code == 403
    assert (await client.get("/ordenes/999")).status_code == 404
    assert (await client.get("/ordenes")).status_code == 403


async def test_lo_propio_sin_ficha_devuelve_vacio(client):
    cookie(client)
    assert (await client.get("/mis-vehiculos")).json() == []
    assert (await client.get("/mis-ordenes")).json()["total"] == 0


async def test_cancelar_permiso_antes_estado_y_dueno(client):
    cookie(client, "cliente@example.com")
    assert (await client.post("/ordenes/2/cancelar")).status_code == 403
    assert (await client.post("/ordenes/1/cancelar")).status_code == 200
    assert (await client.post("/ordenes/1/cancelar")).status_code == 409


async def test_terminar_solo_asignado_o_admin(client):
    cookie(client, "mecanico2@example.com")
    assert (await client.post("/ordenes/2/terminar")).status_code == 403
    cookie(client, "mecanico@example.com")
    assert (
        await client.post("/ordenes/2/terminar")
    ).status_code == 409  # stock insuficiente
    cookie(client)
    assert (await client.post("/ordenes/2/terminar")).status_code == 409


async def test_iniciar_usa_actor_real_y_exige_mecanico(client):
    cookie(client)
    assert (await client.post("/ordenes/1/iniciar")).status_code == 403
    cookie(client, "mecanico2@example.com")
    response = await client.post("/ordenes/1/iniciar")
    assert response.status_code == 200
    assert response.json()["mecanico_id"] == 5
    assert response.json()["historial"][-1]["usuario_id"] == 5


async def test_crear_orden_usa_actor_real(client):
    cookie(client)
    response = await client.post(
        "/ordenes",
        json={
            "vehiculo_id": 1,
            "falla": "Prueba",
            "items": [{"repuesto_id": 1, "cantidad": 1}],
        },
    )
    assert response.status_code == 201
    assert response.json()["historial"][0]["usuario_id"] == 1
    cookie(client, "mecanico@example.com")
    assert (
        await client.post(
            "/ordenes",
            json={
                "vehiculo_id": 1,
                "falla": "Prueba",
                "items": [{"repuesto_id": 1, "cantidad": 1}],
            },
        )
    ).status_code == 403


async def test_alta_personal_duplicada_y_revocar_inexistente(client):
    cookie(client)
    payload = {
        "email": "admin@example.com",
        "nombre": "Otro",
        "password": "Temporal123!",
        "roles": ["ADMIN"],
    }
    assert (await client.post("/usuarios", json=payload)).status_code == 409
    assert (await client.delete("/usuarios/3/roles/MECANICO")).status_code == 404


async def test_alta_cliente_registra_evento(client):
    response = await client.post(
        "/auth/registro",
        json={
            "email": "alta@test.com",
            "nombre": "Cliente nuevo",
            "password": "Cliente123!",
            "documento": "40555666",
        },
    )
    assert response.status_code == 201
    cookie(client)
    filas = (await client.get("/eventos")).json()["items"]
    assert any(
        e["actor"] == "alta@test.com" and "Alta de cliente" in e["accion"]
        for e in filas
    )


async def test_eventos_roles_password_y_cookie_segura(client):
    cookie(client)
    assert (
        await client.post(
            "/usuarios/3/roles",
            json={"rol": "MECANICO", "vence_en": "2030-01-01T03:00:00+03:00"},
        )
    ).status_code == 201
    assert (await client.delete("/usuarios/3/roles/MECANICO")).status_code == 200
    response = await client.post(
        "/auth/cambiar-password",
        json={"password_actual": "Admin1234!", "password_nueva": "AdminNueva123!"},
    )
    assert response.status_code == 200
    encabezado = response.headers["set-cookie"].lower()
    assert (
        "httponly" in encabezado
        and "samesite=lax" in encabezado
        and "max-age=" in encabezado
    )
    assert "access_token" not in response.json()
    filas = (await client.get("/eventos")).json()["items"]
    assert {e["accion"] for e in filas}.issuperset(
        {
            "Asignar MECANICO al usuario 3",
            "Revocar MECANICO al usuario 3",
            "Cambio de contraseña",
        }
    )
    assert all(
        e["actor"] == "admin@example.com"
        for e in filas
        if e["accion"] != "Carga de los datos iniciales"
    )


async def test_password_y_alta_calculan_bcrypt_sin_transaccion(client, monkeypatch):
    from app.modules.usuarios import service

    original = service.hash_password

    async def verificar_sin_conexion(password, settings=None):
        # El backend tiene sólo una conexión externa del fixture; las sesiones de la
        # petición deben haber terminado su lectura antes de calcular el hash.
        assert not any(session.in_transaction() for session in sesiones)
        return await original(password, settings)

    sesiones = []
    from app.core.database import get_session

    async def sesion_controlada():
        async with app.state.session_factory() as session:
            sesiones.append(session)
            yield session

    app.dependency_overrides[get_session] = sesion_controlada
    monkeypatch.setattr(service, "hash_password", verificar_sin_conexion)
    try:
        cookie(client)
        assert (
            await client.post(
                "/usuarios",
                json={
                    "email": "trabajo@example.com",
                    "nombre": "Trabajo",
                    "password": "Temporal123!",
                    "roles": ["MECANICO"],
                },
            )
        ).status_code == 201
        assert (
            await client.post(
                "/auth/cambiar-password",
                json={
                    "password_actual": "Admin1234!",
                    "password_nueva": "AdminNueva123!",
                },
            )
        ).status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.parametrize(
    "path", ["/usuarios/1/roles", "/eventos", "/mis-vehiculos", "/mis-ordenes"]
)
async def test_nuevas_rutas_sin_cookie_401(client, path):
    assert (await client.get(path)).status_code == 401


@pytest.mark.parametrize(
    "path", ["/usuarios/1/roles", "/eventos", "/mis-vehiculos", "/mis-ordenes"]
)
async def test_nuevas_rutas_password_pendiente_403(client, path):
    cookie(client, "nuevo@example.com")
    assert (await client.get(path)).status_code == 403


@pytest.mark.parametrize("cambio", ["revocado", "vencido"])
async def test_mecanico_asignado_requiere_rol_vigente_para_terminar(client, cambio):
    async with app.state.session_factory() as session:
        valores = (
            {"revocada_en": datetime.now(UTC)}
            if cambio == "revocado"
            else {"vence_en": datetime.now(UTC) - timedelta(seconds=1)}
        )
        await session.execute(
            update(AsignacionRol).where(AsignacionRol.usuario_id == 4).values(**valores)
        )
        await session.commit()
    cookie(client, "mecanico@example.com", ["MECANICO"])
    assert (await client.post("/ordenes/2/terminar")).status_code == 403


async def test_repuestos_usan_admin_actor_real(client):
    cookie(client, "admin2@example.com")
    response = await client.post(
        "/repuestos",
        json={
            "codigo": "ACTOR",
            "descripcion": "Actor real",
            "precio": "100.00",
            "stock_inicial": 2,
        },
    )
    assert response.status_code == 201
    repuesto_id = response.json()["id"]
    movimientos = (await client.get(f"/repuestos/{repuesto_id}/movimientos")).json()
    assert movimientos[0]["usuario_id"] == 2
    assert (
        await client.patch(f"/repuestos/{repuesto_id}", json={"precio": "120.00"})
    ).status_code == 200
    precios = (await client.get(f"/repuestos/{repuesto_id}/precios")).json()
    assert precios[0]["usuario_id"] == 2
