"""Ejercicio 7 · Integridad: sólo agregado e intento de acceso (PostgreSQL real).

Todo corre dentro de la transacción externa del fixture `auth_client`, que se revierte al
final: las filas que dejan estas pruebas no sobreviven a la ejecución.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.config import get_settings
from app.core.tipos import ahora
from app.modules.usuarios.models import IntentoAcceso
from app.modules.usuarios.repository import IntentoAccesoRepository
from main import app
from test_autorizacion import client  # noqa: F401  fixture con seed
from test_auth import auth_client  # noqa: F401

pytestmark = pytest.mark.asyncio

IP_PRUEBAS = "127.0.0.1"  # la dirección que informa ASGITransport


# --------------------------------------------------------------------------------------
# RN-15 · Disparador de sólo agregado (C-14 desde pytest; el .sql lo repite en psql)
# --------------------------------------------------------------------------------------

SOLO_AGREGADO = ("historial_estado_orden", "movimiento_stock", "historial_precio_repuesto")


@pytest.mark.parametrize("tabla", SOLO_AGREGADO)
@pytest.mark.parametrize("operacion", ["UPDATE", "DELETE"])
async def test_disparador_rechaza_update_y_delete(client, tabla, operacion):
    sql = {
        "UPDATE": f"UPDATE {tabla} SET id = id WHERE id = (SELECT min(id) FROM {tabla})",
        "DELETE": f"DELETE FROM {tabla} WHERE id = (SELECT min(id) FROM {tabla})",
    }[operacion]
    async with app.state.session_factory() as session:
        antes = (await session.execute(text(f"SELECT count(*) FROM {tabla}"))).scalar_one()
        assert antes > 0, "el seed deja al menos una fila en cada tabla de sólo agregado"
        with pytest.raises(DBAPIError) as error:
            async with session.begin_nested():
                await session.execute(text(sql))
        assert f"{tabla} es de sólo agregado: no se permite {operacion}" in str(error.value)
        despues = (await session.execute(text(f"SELECT count(*) FROM {tabla}"))).scalar_one()
        assert despues == antes


async def test_disparador_permite_insert(client):
    async with app.state.session_factory() as session:
        async with session.begin_nested():
            await session.execute(text(
                "INSERT INTO movimiento_stock (repuesto_id, usuario_id, cantidad, motivo) "
                "VALUES (1, 1, 1, 'Prueba de agregado')"))


async def test_estado_fuera_del_catalogo_lo_rechaza_la_clave_foranea(client):
    async with app.state.session_factory() as session:
        with pytest.raises(IntegrityError, match="foreign key"):
            async with session.begin_nested():
                await session.execute(text(
                    "INSERT INTO orden_trabajo (vehiculo_id, estado, falla, total) "
                    "VALUES (1, 'INVENTADO', 'Prueba', 0)"))


async def test_disparador_lo_instala_la_migracion_en_las_tres_tablas(client):
    async with app.state.session_factory() as session:
        filas = (await session.execute(text(
            "SELECT event_object_table, event_manipulation FROM information_schema.triggers "
            "WHERE action_statement LIKE '%rechazar_modificacion%'"))).all()
    assert {(t, op) for t, op in filas} == {
        (t, op) for t in SOLO_AGREGADO for op in ("UPDATE", "DELETE")
    }


# --------------------------------------------------------------------------------------
# RN-08 · Límite de intentos: una consulta, ventana de 60 s, el éxito reinicia la cuenta
# --------------------------------------------------------------------------------------

def _correo() -> str:
    return f"{uuid4().hex[:8]}@test.com"


async def _anotar(email: str, exito: bool, hace_segundos: float = 0) -> None:
    async with app.state.session_factory() as session:
        session.add(IntentoAcceso(email=email, ip=IP_PRUEBAS, exito=exito,
                                  cuando=ahora() - timedelta(seconds=hace_segundos)))
        await session.commit()


async def _login(client, email, password="Incorrecta123"):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_seis_fallos_seguidos_el_sexto_es_429_sin_hash(client, monkeypatch):
    """C-05: el sexto responde 429 con Retry-After y no calcula ningún hash."""
    from app.modules.usuarios import service as servicio

    email = "admin@example.com"
    for _ in range(5):
        assert (await _login(client, email)).status_code == 401

    verificaciones = []
    original = servicio.verificar_password

    async def contar(*args, **kwargs):
        verificaciones.append(args)
        return await original(*args, **kwargs)
    monkeypatch.setattr(servicio, "verificar_password", contar)

    sexto = await _login(client, email, password="Admin1234!")  # aun la correcta
    assert sexto.status_code == 429
    assert 1 <= int(sexto.headers["Retry-After"]) <= 60
    assert verificaciones == []
    async with app.state.session_factory() as session:
        fallos = (await session.execute(select(func.count()).select_from(IntentoAcceso).where(
            IntentoAcceso.email == email, IntentoAcceso.exito.is_(False)))).scalar_one()
    assert fallos == 5


async def test_fallos_fuera_de_la_ventana_no_cuentan(client):
    email = _correo()
    for _ in range(5):
        await _anotar(email, exito=False, hace_segundos=120)
    assert (await _login(client, email)).status_code == 401


async def test_ventana_mezclada_cuenta_solo_los_recientes(client):
    email = _correo()
    for _ in range(3):
        await _anotar(email, exito=False, hace_segundos=90)
    for _ in range(4):
        await _anotar(email, exito=False, hace_segundos=5)
    assert (await _login(client, email)).status_code == 401  # 4 recientes: todavía no
    assert (await _login(client, email)).status_code == 429  # 5 recientes


async def test_login_correcto_reinicia_la_cuenta(client):
    email = "recepcion@example.com"
    for _ in range(4):
        assert (await _login(client, email)).status_code == 401
    assert (await _login(client, email, "Recepcion1234!")).status_code == 200
    for _ in range(4):
        assert (await _login(client, email)).status_code == 401
    # Los 8 fallos siguen en la tabla, pero sólo 4 cuentan.
    assert (await _login(client, email, "Recepcion1234!")).status_code == 200


async def test_otra_ip_no_comparte_el_limite(client):
    email = _correo()
    async with app.state.session_factory() as session:
        for _ in range(5):
            session.add(IntentoAcceso(email=email, ip="10.0.0.9", exito=False))
        await session.commit()
    assert (await _login(client, email)).status_code == 401


async def test_retry_after_se_calcula_desde_el_fallo_mas_viejo_de_la_ventana(client):
    email = _correo()
    await _anotar(email, exito=False, hace_segundos=50)
    for _ in range(4):
        await _anotar(email, exito=False, hace_segundos=1)
    respuesta = await _login(client, email)
    assert respuesta.status_code == 429
    assert 9 <= int(respuesta.headers["Retry-After"]) <= 11


async def test_comprobar_el_limite_cuesta_una_consulta(client):
    """El repositorio trae los fallos que cuentan en una consulta (subconsulta incluida)."""
    email = _correo()
    for _ in range(5):
        await _anotar(email, exito=False)
    settings = get_settings()
    sentencias = []

    def anotar(conn, cursor, statement, *args):
        sentencias.append(statement)
    motor = app.state.engine.sync_engine
    event.listen(motor, "before_cursor_execute", anotar)
    try:
        async with app.state.session_factory() as session:
            fallos = await IntentoAccesoRepository(session, IntentoAcceso).get_fallos_recientes(
                email, IP_PRUEBAS, settings.LOGIN_VENTANA_SEGUNDOS, limite=settings.LOGIN_MAX_FALLOS)
    finally:
        event.remove(motor, "before_cursor_execute", anotar)
    consultas = [s for s in sentencias if s.lstrip().upper().startswith("SELECT")]
    assert len(consultas) == 1
    assert len(fallos) == 5


async def test_login_bloqueado_hace_una_sola_consulta(client):
    """El 429 sale con una consulta a la base: ni la del usuario, ni la del hash."""
    email = _correo()
    for _ in range(5):
        await _anotar(email, exito=False)
    sentencias = []

    def anotar(conn, cursor, statement, *args):
        sentencias.append(statement)
    motor = app.state.engine.sync_engine
    event.listen(motor, "before_cursor_execute", anotar)
    try:
        assert (await _login(client, email)).status_code == 429
    finally:
        event.remove(motor, "before_cursor_execute", anotar)
    assert len([s for s in sentencias if s.lstrip().upper().startswith("SELECT")]) == 1
