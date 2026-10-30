"""Contratos de persistencia y atomicidad con PostgreSQL real."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
import pytest

from app.core.config import get_settings
from app.core.errores import ErrorConflicto
from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente
from app.modules.clientes.models import Vehiculo
from app.modules.clientes.repository import VehiculoRepository
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ordenes.models import HistorialEstadoOrden, OrdenTrabajo
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork
from app.modules.repuestos.models import HistorialPrecio
from app.modules.repuestos.models import MovimientoStock, Repuesto
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork
from app.modules.usuarios.models import AsignacionRol, Usuario
from app.modules.usuarios.models import IntentoAcceso
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork
from main import app
from test_auth import auth_client
from test_autorizacion import client, cookie


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [RuntimeError("commit fallido"), IntegrityError("", {}, Exception())])
async def test_uow_revierte_si_falla_commit_sin_cerrar_sesion(error):
    session = AsyncMock()
    session.commit.side_effect = error
    with pytest.raises(type(error)):
        async with UnitOfWork(session):
            pass
    session.rollback.assert_awaited_once()
    session.close.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("falla", [False, True])
async def test_uow_confirma_o_revierte_sin_cerrar_sesion(falla):
    session = AsyncMock()
    if falla:
        with pytest.raises(ValueError):
            async with UnitOfWork(session):
                raise ValueError("operación fallida")
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()
    else:
        async with UnitOfWork(session):
            pass
        session.commit.assert_awaited_once()
        session.rollback.assert_not_awaited()
    session.close.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("cantidad,esperado", [(3, 13), (-2, 8)])
async def test_stock_mover_actualiza_stock_y_movimiento(client, cantidad, esperado):
    from app.modules.repuestos.repository import StockRepository

    async with app.state.session_factory() as session:
        async with UnitOfWork(session):
            repuesto = await session.get(Repuesto, 1)
            movimiento = await StockRepository(session).mover(
                repuesto, cantidad, "Prueba de movimiento", usuario_id=1,
            )
            assert repuesto.stock == esperado
            assert movimiento.cantidad == cantidad
        assert (await session.get(Repuesto, 1)).stock == esperado
        movimientos = (await session.execute(
            select(MovimientoStock).where(MovimientoStock.repuesto_id == 1)
        )).scalars().all()
        assert len(movimientos) == 2
        assert sum(m.cantidad for m in movimientos) == esperado


@pytest.mark.asyncio
@pytest.mark.parametrize("cantidad", [-11, 0])
async def test_stock_mover_rechaza_y_no_escribe(client, cantidad):
    from app.modules.repuestos.repository import StockRepository

    async with app.state.session_factory() as session:
        with pytest.raises(ErrorConflicto):
            async with UnitOfWork(session):
                repuesto = await session.get(Repuesto, 1)
                await StockRepository(session).mover(repuesto, cantidad, "Inválido", usuario_id=1)
        assert (await session.get(Repuesto, 1)).stock == 10
        total = (await session.execute(select(func.count()).select_from(MovimientoStock))).scalar_one()
        assert total == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("telefono", [None, "2615551234"])
async def test_registro_guarda_documento_y_telefono_reales(client, telefono):
    payload = dict(email="registro@test.com", nombre="Registro real",
                   password="Password123", documento="12345678", telefono=telefono)
    response = await client.post("/auth/registro", json=payload)
    assert response.status_code == 201
    async with app.state.session_factory() as session:
        ficha = (await session.execute(select(Cliente).where(Cliente.documento == "12345678"))).scalar_one()
        assert ficha.telefono == telefono
        assert ficha.usuario_id == response.json()["id"]
        rol = (await session.execute(select(AsignacionRol.rol).where(AsignacionRol.usuario_id == ficha.usuario_id))).scalar_one()
        assert rol == "CLIENTE"


@pytest.mark.asyncio
@pytest.mark.parametrize("documento", [None, "30111222"])
async def test_registro_rechazado_no_deja_usuario_ni_rol(client, documento):
    payload = dict(email="rechazado@test.com",
                   nombre="Rechazado", password="Password123")
    if documento is not None:
        payload["documento"] = documento
    response = await client.post("/auth/registro", json=payload)
    assert response.status_code == (422 if documento is None else 409)
    async with app.state.session_factory() as session:
        assert (await session.execute(select(Usuario).where(Usuario.email == payload["email"]))).scalar_one_or_none() is None
        assert (await session.execute(select(func.count()).select_from(AsignacionRol))).scalar_one() == 7
        assert (await session.get(Cliente, 1)).usuario_id == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("operacion,esperadas", [("alta", [2]), ("reponer", [3]), ("terminar", [-1, -4])])
async def test_operaciones_usan_punto_unico_stock(client, monkeypatch, operacion, esperadas):
    from app.modules.repuestos.repository import StockRepository

    cantidades = []
    original = StockRepository.mover

    async def observar(self, repuesto, cantidad, *args, **kwargs):
        cantidades.append(cantidad)
        return await original(self, repuesto, cantidad, *args, **kwargs)
    monkeypatch.setattr(StockRepository, "mover", observar)
    cookie(client)
    if operacion == "alta":
        response = await client.post("/repuestos", json=dict(codigo="PRUEBA", descripcion="Prueba", precio="5.00", stock_inicial=2))
        assert response.status_code == 201
    elif operacion == "reponer":
        response = await client.post("/repuestos/1/reponer", json=dict(cantidad=3, motivo="Entrada"))
        assert response.status_code == 200
    else:
        cookie(client, "mecanico@example.com")
        assert (await client.post("/ordenes/1/iniciar")).status_code == 200
        response = await client.post("/ordenes/1/terminar")
        assert response.status_code == 200
    assert cantidades == esperadas


@pytest.mark.asyncio
async def test_seed_usa_punto_unico_stock(client, monkeypatch):
    from app.modules.repuestos.repository import StockRepository
    from seed import cargar

    cantidades = []
    original = StockRepository.mover

    async def observar(self, repuesto, cantidad, *args, **kwargs):
        cantidades.append(cantidad)
        return await original(self, repuesto, cantidad, *args, **kwargs)
    monkeypatch.setattr(StockRepository, "mover", observar)
    async with app.state.session_factory() as session:
        await cargar(session)
        await session.commit()
    assert cantidades == [10, 4, 2, 20]


async def snapshot_orden():
    async with app.state.session_factory() as session:
        stocks = (await session.execute(select(Repuesto.id, Repuesto.stock).order_by(Repuesto.id))).all()
        estados = (await session.execute(select(OrdenTrabajo.id, OrdenTrabajo.estado).order_by(OrdenTrabajo.id))).all()
        movimientos = (await session.execute(select(MovimientoStock.id, MovimientoStock.cantidad).order_by(MovimientoStock.id))).all()
        historial = (await session.execute(select(HistorialEstadoOrden.id, HistorialEstadoOrden.hasta_estado).order_by(HistorialEstadoOrden.id))).all()
        return stocks, estados, movimientos, historial


@pytest.mark.asyncio
@pytest.mark.parametrize("operacion", ["crear", "iniciar", "terminar", "cancelar"])
async def test_orden_usa_un_bloque_y_responde_historial_actualizado(client, monkeypatch, operacion):
    if operacion == "terminar":
        cookie(client, "mecanico@example.com")
        assert (await client.post("/ordenes/1/iniciar")).status_code == 200
    salidas = []
    original = UnitOfWork.__aexit__

    async def observar(self, *args):
        if isinstance(self, OrdenesUnitOfWork):
            salidas.append(self)
        return await original(self, *args)
    monkeypatch.setattr(UnitOfWork, "__aexit__", observar)
    if operacion == "crear":
        cookie(client)
        response = await client.post("/ordenes", json=dict(vehiculo_id=1, falla="Prueba", items=[dict(repuesto_id=1, cantidad=1)]))
        estado = "PENDIENTE"
    else:
        cookie(client, "mecanico@example.com" if operacion in ("iniciar",
               "terminar") else "admin@example.com")
        response = await client.post(f"/ordenes/1/{operacion}")
        estado = {"iniciar": "EN_REPARACION", "terminar": "TERMINADA",
                  "cancelar": "CANCELADA"}[operacion]
    assert response.status_code in (200, 201)
    assert len(salidas) == 1
    assert response.json()["estado"] == estado
    assert response.json()["historial"][-1]["hasta_estado"] == estado


@pytest.mark.asyncio
@pytest.mark.parametrize("segundo_item", [False, True])
async def test_terminar_insuficiente_revierte_las_cuatro_escrituras(client, segundo_item):
    cookie(client, "mecanico@example.com")
    if segundo_item:
        assert (await client.post("/ordenes/1/iniciar")).status_code == 200
        from app.modules.repuestos.repository import StockRepository
        async with app.state.session_factory() as session:
            async with UnitOfWork(session):
                await StockRepository(session).mover(await session.get(Repuesto, 4), -18, "Salida previa", usuario_id=1)
    antes = await snapshot_orden()
    response = await client.post(f"/ordenes/{1 if segundo_item else 2}/terminar")
    assert response.status_code == 409
    assert await snapshot_orden() == antes


@pytest.mark.asyncio
async def test_terminar_fallo_final_revierte_stock_movimientos_y_estado(client, monkeypatch):
    from app.modules.ordenes.repository import HistorialEstadoOrdenRepository

    cookie(client, "mecanico@example.com")
    assert (await client.post("/ordenes/1/iniciar")).status_code == 200
    antes = await snapshot_orden()

    async def fallar(self, entidad):
        raise ErrorConflicto("Fallo simulado al guardar historial")
    monkeypatch.setattr(HistorialEstadoOrdenRepository, "add", fallar)
    assert (await client.post("/ordenes/1/terminar")).status_code == 409
    assert await snapshot_orden() == antes


@pytest.mark.asyncio
@pytest.mark.parametrize("fallar", [False, True])
async def test_precio_e_historial_son_atomicos(client, monkeypatch, fallar):
    from app.modules.repuestos.repository import RepuestoRepository

    if fallar:
        original = RepuestoRepository.update

        async def fallo_despues_de_flush(self, entidad):
            await original(self, entidad)
            raise ErrorConflicto("Fallo posterior al cambio de precio")
        monkeypatch.setattr(RepuestoRepository, "update", fallo_despues_de_flush)
    cookie(client)
    response = await client.patch("/repuestos/1", json={"precio": "9200.00"})
    assert response.status_code == (409 if fallar else 200)
    async with app.state.session_factory() as session:
        assert str((await session.get(Repuesto, 1)).precio) == ("8500.00" if fallar else "9200.00")
        assert (await session.execute(select(func.count()).select_from(HistorialPrecio))).scalar_one() == (1 if fallar else 2)
    if not fallar:
        assert (await client.patch("/repuestos/1", json={"descripcion": "Sólo texto"})).status_code == 200
        assert len((await client.get("/repuestos/1/precios")).json()) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("falla", [False, True])
async def test_acceso_uow_crea_confirma_y_cierra_su_propia_sesion(falla):
    from app.modules.usuarios.unit_of_work import AccesoUnitOfWork

    session = AsyncMock()
    factory = Mock(return_value=session)
    uow = AccesoUnitOfWork(factory)
    if falla:
        with pytest.raises(ValueError):
            async with uow:
                assert uow.intentos.session is session
                raise ValueError("Login rechazado")
    else:
        async with uow:
            assert uow.intentos.session is session
    factory.assert_called_once_with()
    session.commit.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_router_login_inyecta_uows_sin_abrirlos(client, monkeypatch):
    from app.modules.usuarios.service import ServiceAuth
    from app.modules.usuarios.unit_of_work import AccesoUnitOfWork, UsuariosUnitOfWork

    recibidos = {}

    async def recibir(**kwargs):
        recibidos.update(kwargs)
        return {"mensaje": "Prueba de dependencia"}
    monkeypatch.setattr(ServiceAuth, "login", recibir)
    response = await client.post("/auth/login", json=dict(email="admin@example.com", password="Admin1234!"))
    assert response.status_code == 200
    assert isinstance(recibidos.get("uow"), UsuariosUnitOfWork)
    assert isinstance(recibidos.get("acceso"), AccesoUnitOfWork)
    assert not recibidos["uow"].session.in_transaction()


@pytest.mark.asyncio
@pytest.mark.parametrize("dentro_del_acceso", [False, True])
async def test_intento_sobrevive_rollback_peticion_en_sesion_independiente(auth_client, dentro_del_acceso):
    from app.modules.usuarios.unit_of_work import AccesoUnitOfWork

    settings = get_settings()
    assert settings.POSTGRES_PORT == 55432 and settings.POSTGRES_DB.startswith(
        "parcial_")
    factory = async_sessionmaker(app.state.engine, expire_on_commit=False)
    email = f"{uuid4().hex[:8]}@test.com"
    try:
        async with app.state.session_factory() as peticion:
            with pytest.raises(ValueError):
                async with UnitOfWork(peticion):
                    peticion.add(Usuario(email=email, nombre="No persiste",
                                 password_hash="hash de prueba"))
                    await peticion.flush()
                    async with AccesoUnitOfWork(factory) as acceso:
                        assert acceso.session is not peticion
                        await acceso.intentos.add(IntentoAcceso(email=email, ip="127.0.0.1", exito=False))
                        if dentro_del_acceso:
                            raise ValueError("Login rechazado")
                    raise ValueError("Petición rechazada")
        async with factory() as verificacion:
            assert (await verificacion.execute(select(IntentoAcceso).where(IntentoAcceso.email == email))).scalar_one().exito is False
            assert (await verificacion.execute(select(Usuario).where(Usuario.email == email))).scalar_one_or_none() is None
    finally:
        # Sólo la fila generada por esta prueba, en la base desechable explícita.
        async with factory() as limpieza:
            await limpieza.execute(delete(IntentoAcceso).where(IntentoAcceso.email == email))
            await limpieza.commit()


@pytest.mark.asyncio
async def test_repositorio_base_flush_sin_commit_y_crud(client, monkeypatch):
    async with app.state.session_factory() as session:
        confirmar = AsyncMock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", confirmar)
        repo = BaseRepository(session, Cliente)
        async with UnitOfWork(session):
            ficha = await repo.add(Cliente(nombre="Nuevo", documento="77777777"))
            assert ficha.id is not None
            assert (await repo.get_by_id(ficha.id)).nombre == "Nuevo"
            ficha.nombre = "Actualizado"
            await repo.update(ficha)
            assert (await repo.get_by_id(ficha.id)).nombre == "Actualizado"
            assert await repo.count() == 3
            assert len(await repo.get_all()) == 3
            await repo.delete(ficha)
            assert await repo.get_by_id(ficha.id) is None
            confirmar.assert_not_awaited()
        confirmar.assert_awaited_once()


@pytest.mark.asyncio
async def test_unicidad_falla_en_flush_y_revierte_bloque(client):
    async with app.state.session_factory() as session:
        repo = BaseRepository(session, Cliente)
        with pytest.raises(IntegrityError):
            async with UnitOfWork(session):
                await repo.add(Cliente(nombre="Primero", documento="77777777"))
                await repo.add(Cliente(nombre="Duplicado", documento="30111222"))
        assert await repo.count() == 2
        assert (await session.execute(select(Cliente).where(Cliente.documento == "77777777"))).scalar_one_or_none() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("vehiculo_id", [1, 2])
async def test_softdelete_filtra_sin_borrar_fila(client, vehiculo_id):
    async with app.state.session_factory() as session:
        repo = VehiculoRepository(session, Vehiculo)
        async with UnitOfWork(session):
            vehiculo = await repo.get_by_id(vehiculo_id)
            await repo.soft_delete(vehiculo)
        assert await repo.get_by_id(vehiculo_id) is None
        assert (await repo.get_by_id_including_deleted(vehiculo_id)).borrado_en is not None
        assert await repo.count() == 2
        assert vehiculo_id not in [v.id for v in await repo.get_all()]
        assert not hasattr(BaseRepository, "soft_delete")


@pytest.mark.asyncio
async def test_stock_fallo_movimiento_revierte_update_condicionado(client):
    from app.modules.repuestos.repository import StockRepository

    async with app.state.session_factory() as session:
        with pytest.raises(IntegrityError):
            async with UnitOfWork(session):
                await StockRepository(session).mover(await session.get(Repuesto, 1), 3, "Usuario inexistente", usuario_id=999999)
        assert (await session.get(Repuesto, 1)).stock == 10
        assert (await session.execute(select(func.count()).select_from(MovimientoStock))).scalar_one() == 4


@pytest.mark.asyncio
async def test_registro_fallo_evento_revierte_usuario_rol_y_ficha(client, monkeypatch):
    from app.modules.usuarios.repository import EventoSeguridadRepository

    async def fallar(self, evento):
        raise ErrorConflicto("Evento rechazado")
    monkeypatch.setattr(EventoSeguridadRepository, "add", fallar)
    response = await client.post("/auth/registro", json=dict(email="fallo@test.com", nombre="Prueba", password="Password123", documento="77777777"))
    assert response.status_code == 409
    async with app.state.session_factory() as session:
        assert (await session.execute(select(Usuario).where(Usuario.email == "fallo@test.com"))).scalar_one_or_none() is None
        assert (await session.execute(select(func.count()).select_from(AsignacionRol))).scalar_one() == 7
        assert (await session.execute(select(func.count()).select_from(Cliente))).scalar_one() == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("uow_tipo,atributo,total", [
    (UsuariosUnitOfWork, "usuarios", 7), (UsuariosUnitOfWork, "asignaciones", 7),
    (UsuariosUnitOfWork, "eventos", 1), (UsuariosUnitOfWork, "intentos", 0),
    (ClientesUnitOfWork, "clientes", 2), (ClientesUnitOfWork, "vehiculos", 3),
    (RepuestosUnitOfWork, "repuestos", 4), (RepuestosUnitOfWork, "movimientos", 4),
    (RepuestosUnitOfWork, "precios", 1), (OrdenesUnitOfWork, "ordenes", 2),
    (OrdenesUnitOfWork, "items", 3), (OrdenesUnitOfWork, "historial", 3),
])
async def test_uows_componen_repositorios_con_misma_sesion(client, uow_tipo, atributo, total):
    async with app.state.session_factory() as session:
        uow = uow_tipo(session)
        repo = getattr(uow, atributo)
        assert repo.session is session
        async with uow:
            assert await repo.count() == total
            assert len(await repo.get_all()) == total
        assert (await session.execute(select(1))).scalar_one() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("vehiculo_id", [1, 2])
async def test_catalogo_vacio_responde_conflicto_propio_sin_escribir(client, monkeypatch, vehiculo_id):
    from app.modules.ordenes.repository import EstadoOrdenRepository

    monkeypatch.setattr(EstadoOrdenRepository, "get_by_codigo",
                        AsyncMock(return_value=None))
    cookie(client)
    response = await client.post("/ordenes", json=dict(vehiculo_id=vehiculo_id, falla="Prueba", items=[dict(repuesto_id=1, cantidad=1)]))
    assert response.status_code == 409
    assert response.json()[
        "detail"] == "El catálogo de estados está vacío: falta correr seed.py"
    async with app.state.session_factory() as session:
        assert (await session.execute(select(func.count()).select_from(OrdenTrabajo))).scalar_one() == 2


@pytest.mark.asyncio
async def test_catalogo_es_solo_lectura_y_ordenado(client):
    from app.modules.ordenes.repository import EstadoOrdenRepository

    async with app.state.session_factory() as session:
        repo = EstadoOrdenRepository(session)
        estados = await repo.list_all()
        assert [e.posicion for e in estados] == [1, 2, 3, 4]
        assert [e.codigo for e in estados if e.es_final] == ["TERMINADA", "CANCELADA"]
        assert not any(hasattr(repo, metodo) for metodo in ("add", "update", "delete"))
        assert await repo.get_by_codigo("NO_EXISTE") is None
