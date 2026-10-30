"""Ejercicio 8 · Lecturas sin N+1 y asincronía (PostgreSQL real, todo se revierte al final)."""

import ast
import asyncio
import inspect
import logging
from contextlib import contextmanager

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.orm import class_mapper

from app import modelos
from main import app
from test_autorizacion import client, cookie  # noqa: F401  fixture con seed
from test_auth import auth_client  # noqa: F401

pytestmark = pytest.mark.asyncio


@contextmanager
def consultas():
    """Anota cada sentencia SQL que sale hacia la base mientras dura el bloque."""
    sentencias: list[str] = []

    def anotar(conn, cursor, statement, *args):
        sentencias.append(statement.lstrip())
    motor = app.state.engine.sync_engine
    event.listen(motor, "before_cursor_execute", anotar)
    try:
        yield sentencias
    finally:
        event.remove(motor, "before_cursor_execute", anotar)


def selects(sentencias: list[str]) -> list[str]:
    return [s for s in sentencias if s.upper().startswith("SELECT")]


async def crear_orden(client, repuestos: list[int], cantidad: int = 1) -> int:
    cookie(client, "admin@example.com")
    respuesta = await client.post("/ordenes", json={
        "vehiculo_id": 1,
        "falla": "Prueba de consultas",
        "items": [{"repuesto_id": r, "cantidad": cantidad} for r in repuestos],
    })
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


# --------------------------------------------------------------------------------------
# C-15 · El detalle se resuelve con un número fijo de consultas
# --------------------------------------------------------------------------------------

async def test_detalle_misma_cantidad_de_consultas_con_2_y_4_items(client):
    con_dos = await crear_orden(client, [1, 2])
    con_cuatro = await crear_orden(client, [1, 2, 3, 4])
    cookie(client, "admin@example.com")

    with consultas() as dos:
        r2 = await client.get(f"/ordenes/{con_dos}")
    with consultas() as cuatro:
        r4 = await client.get(f"/ordenes/{con_cuatro}")

    assert r2.status_code == r4.status_code == 200
    assert len(r2.json()["items"]) == 2 and len(r4.json()["items"]) == 4
    assert len(selects(dos)) == len(selects(cuatro))
    # orden+vehículo+cliente (un JOIN), ítems, repuestos e historial: cuatro, y no más.
    # Las demás consultas son de la autenticación (usuario y roles vigentes), siempre las mismas.
    tablas = ("FROM orden_trabajo", "FROM item_orden", "FROM repuesto", "FROM vehiculo",
              "FROM cliente", "FROM historial_estado_orden")
    detalle = [s for s in selects(cuatro) if any(t in s for t in tablas)]
    assert len(detalle) == 4, detalle


async def test_detalle_trae_vehiculo_y_cliente_en_un_join(client):
    cookie(client, "admin@example.com")
    with consultas() as sentencias:
        assert (await client.get("/ordenes/1")).status_code == 200
    principal = next(s for s in selects(sentencias) if s.find("FROM orden_trabajo") >= 0)
    assert "JOIN vehiculo" in principal and "JOIN cliente" in principal


async def test_crear_orden_no_consulta_por_cada_item(client):
    with consultas() as dos:
        await crear_orden(client, [1, 2])
    with consultas() as cuatro:
        await crear_orden(client, [1, 2, 3, 4])
    assert len(selects(dos)) == len(selects(cuatro))


async def test_terminar_orden_no_lee_por_cada_item(client, monkeypatch):
    monkeypatch.setattr("app.modules.ordenes.router.avisar_cliente", _aviso_nulo)
    una = await crear_orden(client, [1])
    tres = await crear_orden(client, [1, 2, 4])
    cookie(client, "mecanico@example.com")
    for orden in (una, tres):
        assert (await client.post(f"/ordenes/{orden}/iniciar")).status_code == 200

    with consultas() as con_una:
        assert (await client.post(f"/ordenes/{una}/terminar")).status_code == 200
    with consultas() as con_tres:
        assert (await client.post(f"/ordenes/{tres}/terminar")).status_code == 200
    # Las escrituras sí crecen (un UPDATE de stock y un INSERT de movimiento por ítem);
    # las lecturas no.
    assert len(selects(con_una)) == len(selects(con_tres))


async def test_listados_de_ordenes_no_crecen_con_la_pagina(client):
    for _ in range(3):
        await crear_orden(client, [1])
    cookie(client, "admin@example.com")
    with consultas() as chica:
        assert (await client.get("/ordenes?size=1")).status_code == 200
    with consultas() as grande:
        assert (await client.get("/ordenes?size=5")).status_code == 200
    assert len(selects(chica)) == len(selects(grande))


# --------------------------------------------------------------------------------------
# Sin carga perezosa y sin llamadas bloqueantes
# --------------------------------------------------------------------------------------

async def test_toda_relacion_prohibe_la_carga_perezosa():
    for nombre in modelos.__all__:
        for relacion in class_mapper(getattr(modelos, nombre)).relationships:
            assert relacion.lazy == "raise_on_sql", f"{nombre}.{relacion.key}"


async def test_todos_los_handlers_son_async_def():
    sincronicos = [
        f"{sorted(r.methods)} {r.path}" for r in app.routes
        if isinstance(r, APIRoute) and not inspect.iscoroutinefunction(r.endpoint)
    ]
    assert sincronicos == []


async def test_aviso_es_corrutina_y_no_bloquea():
    from app.modules.ordenes.avisos import avisar_cliente

    assert inspect.iscoroutinefunction(avisar_cliente)
    arbol = ast.parse(inspect.getsource(avisar_cliente))
    llamadas = {ast.unparse(n.func) for n in ast.walk(arbol) if isinstance(n, ast.Call)}
    esperas = [n for n in ast.walk(arbol) if isinstance(n, ast.Await)
               and ast.unparse(n.value) == "asyncio.sleep(0.5)"]
    assert len(esperas) == 1
    assert "time.sleep" not in llamadas


# --------------------------------------------------------------------------------------
# Aviso en segundo plano (BackgroundTasks)
# --------------------------------------------------------------------------------------

async def _aviso_nulo(*args, **kwargs):
    return None


async def test_terminar_agenda_el_aviso_con_datos_de_la_orden(client, monkeypatch):
    avisos = []

    async def anotar(**datos):
        avisos.append(datos)
    monkeypatch.setattr("app.modules.ordenes.router.avisar_cliente", anotar)

    orden = await crear_orden(client, [1])
    cookie(client, "mecanico@example.com")
    assert (await client.post(f"/ordenes/{orden}/iniciar")).status_code == 200
    assert avisos == []  # iniciar no avisa
    assert (await client.post(f"/ordenes/{orden}/terminar")).status_code == 200
    assert avisos == [{"orden_id": orden, "cliente": "Laura Cliente", "patente": avisos[0]["patente"]}]
    assert avisos[0]["patente"]


@pytest.mark.parametrize("caso", ["sin_stock", "sin_permiso", "estado"])
async def test_terminar_fallido_no_agenda_aviso(client, monkeypatch, caso):
    avisos = []

    async def anotar(**datos):
        avisos.append(datos)
    monkeypatch.setattr("app.modules.ordenes.router.avisar_cliente", anotar)

    if caso == "sin_stock":  # C-11: la orden 2 pide 4 bujías y hay 2
        cookie(client, "mecanico@example.com")
        esperado, orden = 409, 2
    elif caso == "sin_permiso":  # la orden 2 es de mecanico@, no de mecanico2@
        cookie(client, "mecanico2@example.com")
        esperado, orden = 403, 2
    else:  # la orden 1 está PENDIENTE
        cookie(client, "admin@example.com")
        esperado, orden = 409, 1
    assert (await client.post(f"/ordenes/{orden}/terminar")).status_code == esperado
    assert avisos == []


async def test_commit_fallido_no_agenda_aviso(client, monkeypatch):
    """«Sólo si la operación se confirmó»: si el commit falla, no hay aviso."""
    from app.core.unit_of_work import UnitOfWork
    from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork

    avisos = []

    async def anotar(**datos):
        avisos.append(datos)
    monkeypatch.setattr("app.modules.ordenes.router.avisar_cliente", anotar)

    orden = await crear_orden(client, [1])
    cookie(client, "mecanico@example.com")
    assert (await client.post(f"/ordenes/{orden}/iniciar")).status_code == 200

    original = UnitOfWork.__aexit__

    async def commit_que_falla(self, exc_type, exc, tb):
        if isinstance(self, OrdenesUnitOfWork) and exc_type is None:
            await self.session.rollback()
            raise RuntimeError("el commit falló")
        return await original(self, exc_type, exc, tb)
    monkeypatch.setattr(UnitOfWork, "__aexit__", commit_que_falla)

    # Un cliente que no re-lanza la excepción de la app, para ver el 500 que recibe el usuario.
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False),
                           base_url="http://test", cookies=dict(client.cookies)) as otro:
        respuesta = await otro.post(f"/ordenes/{orden}/terminar")
    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "Error interno del servidor"}
    assert avisos == []


async def test_aviso_corre_despues_de_enviar_la_respuesta(client, monkeypatch):
    enviados: list[str] = []
    momento_del_aviso: list[list[str]] = []

    async def anotar(**datos):
        momento_del_aviso.append(list(enviados))
    monkeypatch.setattr("app.modules.ordenes.router.avisar_cliente", anotar)

    async def envoltorio(scope, receive, send):
        async def enviar(mensaje):
            enviados.append(mensaje["type"])
            await send(mensaje)
        await app(scope, receive, enviar)

    orden = await crear_orden(client, [1])
    cookie(client, "mecanico@example.com")
    assert (await client.post(f"/ordenes/{orden}/iniciar")).status_code == 200
    async with AsyncClient(transport=ASGITransport(app=envoltorio), base_url="http://test",
                           cookies=dict(client.cookies)) as observado:
        assert (await observado.post(f"/ordenes/{orden}/terminar")).status_code == 200
    # Cuando el aviso arrancó, la respuesta ya había salido completa.
    assert momento_del_aviso == [["http.response.start", "http.response.body"]]


async def test_aviso_espera_medio_segundo_y_lo_anota_en_el_registro(monkeypatch, caplog):
    from app.modules.ordenes import avisos

    esperas = []
    sleep_real = asyncio.sleep

    async def dormir(segundos):
        esperas.append(segundos)
        await sleep_real(0)
    monkeypatch.setattr(avisos.asyncio, "sleep", dormir)

    with caplog.at_level(logging.INFO, logger="taller.avisos"):
        await avisos.avisar_cliente(orden_id=7, cliente="Laura Cliente", patente="AC456EF")
    assert esperas == [0.5]
    assert any("orden 7" in r.getMessage() and "AC456EF" in r.getMessage() and
               "Laura Cliente" in r.getMessage() for r in caplog.records)
