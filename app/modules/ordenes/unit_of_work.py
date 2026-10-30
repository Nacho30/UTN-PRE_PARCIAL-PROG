"""Unit of Work del módulo de órdenes de trabajo."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Vehiculo
from app.modules.clientes.repository import VehiculoRepository
from app.modules.ordenes.models import (
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.ordenes.repository import (
    EstadoOrdenRepository,
    HistorialEstadoOrdenRepository,
    ItemOrdenRepository,
    OrdenTrabajoRepository,
)
from app.modules.repuestos.models import MovimientoStock, Repuesto
from app.modules.repuestos.repository import (
    MovimientoStockRepository,
    RepuestoRepository,
    StockRepository,
)


class OrdenesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.ordenes = OrdenTrabajoRepository(session, OrdenTrabajo)
        self.estados = EstadoOrdenRepository(session)
        self.items = ItemOrdenRepository(session, ItemOrden)
        self.historial = HistorialEstadoOrdenRepository(session, HistorialEstadoOrden)
        self.vehiculos = VehiculoRepository(session, Vehiculo)
        self.repuestos = RepuestoRepository(session, Repuesto)
        self.movimientos = MovimientoStockRepository(session, MovimientoStock)
        self.stock = StockRepository(session)


async def get_ordenes_uow(session: AsyncSession = Depends(get_session)) -> OrdenesUnitOfWork:
    return OrdenesUnitOfWork(session)
