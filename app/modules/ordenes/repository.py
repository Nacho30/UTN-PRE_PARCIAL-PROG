"""Repositorios del módulo de órdenes de trabajo."""

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import (
    EstadoOrden,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)


class EstadoOrdenRepository:
    """Catálogo de estados de orden. De sólo lectura, no hereda de BaseRepository."""

    def __init__(self, session) -> None:
        self.session = session

    async def list_all(self) -> Sequence[EstadoOrden]:
        stmt = select(EstadoOrden).order_by(EstadoOrden.posicion)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_codigo(self, codigo: str) -> EstadoOrden | None:
        stmt = select(EstadoOrden).where(EstadoOrden.codigo == codigo)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(EstadoOrden)
        result = await self.session.execute(stmt)
        return result.scalar_one()


class OrdenTrabajoRepository(BaseRepository[OrdenTrabajo]):
    async def get_de_usuario(
        self, usuario_id: int, page: int, size: int
    ) -> tuple[list[OrdenTrabajo], int]:
        filtro = (
            select(Vehiculo.id).join(Cliente).where(Cliente.usuario_id == usuario_id)
        )
        condiciones = OrdenTrabajo.vehiculo_id.in_(filtro)
        total = (
            await self.session.execute(
                select(func.count()).select_from(OrdenTrabajo).where(condiciones)
            )
        ).scalar_one()
        stmt = (
            select(OrdenTrabajo)
            .where(condiciones)
            .options(selectinload(OrdenTrabajo.vehiculo))
            .order_by(OrdenTrabajo.creada_en.desc(), OrdenTrabajo.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        return list((await self.session.execute(stmt)).scalars().all()), total

    async def get_detalle(self, id: int) -> OrdenTrabajo | None:
        """La orden con todo lo que muestra su detalle, en CUATRO consultas fijas (C-15).

        1. orden + vehículo + cliente, en un JOIN: son muchos-a-uno, una fila cada uno, y
           `joinedload` los trae sin multiplicar filas. `innerjoin`: las claves no son nulas.
        2. los ítems de la orden (`selectinload`: un `IN` con el id de la orden).
        3. el repuesto de cada ítem, todos juntos en un solo `IN`.
        4. el historial de estados.

        Con `joinedload` en las colecciones (ítems, historial) el JOIN repetiría la orden
        por cada ítem × cada línea de historial; `selectinload` las trae aparte y sin
        duplicar. Ninguna cuenta depende de cuántos ítems haya: con 2 o con 40, son cuatro.
        Las relaciones están en `raise_on_sql`, así que si el mapeo leyera algo que no está
        acá, falla en lugar de consultar en silencio.
        """
        stmt = (
            select(OrdenTrabajo)
            .where(OrdenTrabajo.id == id)
            # Refrescar colecciones ya cargadas tras agregar el historial en este UoW.
            .execution_options(populate_existing=True)
            .options(
                joinedload(OrdenTrabajo.vehiculo, innerjoin=True).joinedload(
                    Vehiculo.cliente, innerjoin=True
                ),
                selectinload(OrdenTrabajo.items).selectinload(ItemOrden.repuesto),
                selectinload(OrdenTrabajo.historial),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_paginado(
        self,
        estado: str | None,
        page: int,
        size: int,
    ) -> tuple[list[OrdenTrabajo], int]:
        condiciones = []
        if estado:
            condiciones.append(OrdenTrabajo.estado == estado)

        stmt_count = select(func.count()).select_from(OrdenTrabajo)
        if condiciones:
            stmt_count = stmt_count.where(*condiciones)
        total = (await self.session.execute(stmt_count)).scalar_one()

        stmt_items = (
            select(OrdenTrabajo)
            .options(selectinload(OrdenTrabajo.vehiculo))
            .order_by(OrdenTrabajo.creada_en.desc(), OrdenTrabajo.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        if condiciones:
            stmt_items = stmt_items.where(*condiciones)

        result = await self.session.execute(stmt_items)
        items = list(result.scalars().all())
        return items, total


class ItemOrdenRepository(BaseRepository[ItemOrden]):
    pass


class HistorialEstadoOrdenRepository(BaseRepository[HistorialEstadoOrden]):
    pass
