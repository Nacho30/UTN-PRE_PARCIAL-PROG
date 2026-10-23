"""Deja la base en el estado inicial conocido que usan los casos de prueba.

    python seed.py

Vacía todas las tablas (TRUNCATE ... RESTART IDENTITY: los ids vuelven a empezar en 1) y
carga los datos mínimos. El catálogo de estados va PRIMERO: todo lo que tiene un estado
apunta a él, y sin sus filas no se puede crear ninguna orden. Por eso este script es parte
de la puesta en marcha del proyecto y no un extra para probar.

Las contraseñas son de mentira y viven sólo en este archivo.

TRUNCATE no dispara los triggers de fila de sólo agregado, así que el vaciado funciona aunque
UPDATE y DELETE estén prohibidos en esas tablas.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import modelos  # noqa: F401
from app.core.config import get_settings
from app.core.database import crear_engine, crear_session_factory
from app.core.security import hash_password
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario

TABLAS = (
    "movimiento_stock, historial_precio_repuesto, historial_estado_orden, item_orden, orden_trabajo, "
    "vehiculo, cliente, repuesto, asignacion_rol, intento_acceso, evento_seguridad, usuario, estado_orden"
)

ESTADOS = [
    ("PENDIENTE", "Recibida, a la espera de un mecánico", 1, False),
    ("EN_REPARACION", "Un mecánico la está reparando", 2, False),
    ("TERMINADA", "Reparación terminada; el stock ya se descontó", 3, True),
    ("CANCELADA", "Cancelada antes de empezar", 4, True),
]

# (email, nombre, contraseña de mentira, roles, debe_cambiar_password)
USUARIOS = [
    ("admin@example.com", "Ana Admin", "Admin1234!", ["ADMIN"], False),  # id 1
    ("admin2@example.com", "Andrés Admin", "Admin1234!", ["ADMIN"], False),  # id 2
    ("recepcion@example.com", "Rita Recepción", "Recepcion1234!", ["RECEPCION"], False),  # id 3
    ("mecanico@example.com", "Mario Mecánico", "Mecanico1234!", ["MECANICO"], False),  # id 4
    ("mecanico2@example.com", "Marta Mecánica", "Mecanico1234!", ["MECANICO"], False),  # id 5
    ("cliente@example.com", "Laura Cliente", "Cliente1234!", ["CLIENTE"], False),  # id 6
    ("nuevo@example.com", "Nicolás Nuevo", "Provisoria1234!", ["MECANICO"], True),  # id 7
]


async def cargar(session: AsyncSession) -> None:
    await session.execute(text(f"TRUNCATE {TABLAS} RESTART IDENTITY CASCADE"))

    # 1. Catálogo de estados, primero.
    session.add_all(
        EstadoOrden(codigo=c, descripcion=d, posicion=p, es_final=f) for c, d, p, f in ESTADOS
    )
    await session.flush()

    # 2. Usuarios y roles. Los hashes se calculan en paralelo, fuera del bucle.
    hashes = await asyncio.gather(*(hash_password(pwd) for _, _, pwd, _, _ in USUARIOS))
    usuarios: dict[str, Usuario] = {}
    for (email, nombre, _, roles, cambiar), password_hash in zip(USUARIOS, hashes, strict=True):
        usuario = Usuario(email=email, nombre=nombre, password_hash=password_hash, debe_cambiar_password=cambiar)
        session.add(usuario)
        await session.flush()
        for rol in roles:
            session.add(AsignacionRol(usuario_id=usuario.id, rol=rol))  # otorgada_por nulo: SISTEMA
        usuarios[email] = usuario
    await session.flush()
    admin = usuarios["admin@example.com"].id
    recepcion = usuarios["recepcion@example.com"].id
    mecanico = usuarios["mecanico@example.com"].id

    # 3. Clientes y vehículos.
    laura = Cliente(
        usuario_id=usuarios["cliente@example.com"].id, nombre="Laura Cliente", documento="30111222", telefono="1144445555"
    )
    jorge = Cliente(usuario_id=None, nombre="Jorge Pérez", documento="28999888", telefono="1166667777")
    session.add_all([laura, jorge])
    await session.flush()
    v1 = Vehiculo(cliente_id=laura.id, patente="AB123CD", marca="Ford", modelo="Fiesta", anio=2015)  # id 1
    v2 = Vehiculo(cliente_id=laura.id, patente="AC456EF", marca="Toyota", modelo="Etios", anio=2018)  # id 2
    v3 = Vehiculo(cliente_id=jorge.id, patente="AD789GH", marca="Renault", modelo="Kangoo", anio=2012)  # id 3
    session.add_all([v1, v2, v3])
    await session.flush()

    # 4. Repuestos. Cada stock inicial queda registrado como un movimiento «Stock inicial».
    # (En el ejercicio 6 esto pasa a hacerse por el punto único de stock.)
    filtro = Repuesto(codigo="FIL-001", descripcion="Filtro de aceite", precio=Decimal("8000.00"), stock=10)  # id 1
    pastillas = Repuesto(
        codigo="FRE-010", descripcion="Pastillas de freno delanteras", precio=Decimal("32000.00"), stock=4
    )  # id 2
    bujia = Repuesto(codigo="BUJ-200", descripcion="Bujía", precio=Decimal("4500.00"), stock=2)  # id 3
    aceite = Repuesto(codigo="ACE-530", descripcion="Aceite 5W30 por litro", precio=Decimal("12000.00"), stock=20)  # id 4
    session.add_all([filtro, pastillas, bujia, aceite])
    await session.flush()
    session.add_all(
        MovimientoStock(repuesto_id=r.id, usuario_id=admin, cantidad=r.stock, motivo="Stock inicial")
        for r in (filtro, pastillas, bujia, aceite)
    )

    # 5. Historial de precios: el filtro pasó de 8000 a 8500.
    session.add(
        HistorialPrecio(
            repuesto_id=filtro.id, usuario_id=admin, precio_anterior=Decimal("8000.00"), precio_nuevo=Decimal("8500.00")
        )
    )
    filtro.precio = Decimal("8500.00")
    await session.flush()

    # 6. Órdenes.
    # La 1, PENDIENTE, del primer vehículo de Laura.
    orden1 = OrdenTrabajo(
        vehiculo_id=v1.id,
        estado="PENDIENTE",
        falla="Service de los 60.000 km",
        total=Decimal("56500.00"),  # 1 × 8500 + 4 × 12000
        items=[
            ItemOrden(repuesto_id=filtro.id, cantidad=1, precio_unitario=Decimal("8500.00")),
            ItemOrden(repuesto_id=aceite.id, cantidad=4, precio_unitario=Decimal("12000.00")),
        ],
    )
    # La 2, EN_REPARACION, del vehículo de Jorge, asignada a mecanico@, con 4 bujías cuando hay 2.
    orden2 = OrdenTrabajo(
        vehiculo_id=v3.id,
        mecanico_id=mecanico,
        estado="EN_REPARACION",
        falla="Falla de encendido en frío",
        total=Decimal("18000.00"),  # 4 × 4500
        items=[ItemOrden(repuesto_id=bujia.id, cantidad=4, precio_unitario=Decimal("4500.00"))],
    )
    session.add_all([orden1, orden2])
    await session.flush()
    session.add_all(
        [
            HistorialEstadoOrden(orden_id=orden1.id, desde_estado=None, hasta_estado="PENDIENTE", usuario_id=recepcion),
            HistorialEstadoOrden(orden_id=orden2.id, desde_estado=None, hasta_estado="PENDIENTE", usuario_id=recepcion),
            HistorialEstadoOrden(
                orden_id=orden2.id, desde_estado="PENDIENTE", hasta_estado="EN_REPARACION", usuario_id=mecanico
            ),
        ]
    )

    # 7. Historial de seguridad: una línea con el actor SISTEMA.
    session.add(EventoSeguridad(actor="SISTEMA", accion="Carga de los datos iniciales"))
    await session.flush()


async def main() -> None:
    settings = get_settings()
    engine = crear_engine(settings)
    session_factory = crear_session_factory(engine)
    try:
        async with session_factory() as session, session.begin():
            await cargar(session)
    finally:
        await engine.dispose()
    print("Datos iniciales cargados.")
    for email, _, password, roles, cambiar in USUARIOS:
        extra = " (cambio de contraseña obligatorio)" if cambiar else ""
        print(f"  {email:<24} {password:<16} {', '.join(roles)}{extra}")


if __name__ == "__main__":
    asyncio.run(main())
