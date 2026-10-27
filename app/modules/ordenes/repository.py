"""Repositorios del módulo de órdenes de trabajo."""

from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Vehiculo
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
    async def get_detalle(self, id: int) -> OrdenTrabajo | None:
        stmt = (
            select(OrdenTrabajo)
            .where(OrdenTrabajo.id == id)
            .options(
                selectinload(OrdenTrabajo.vehiculo).selectinload(Vehiculo.cliente),
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
