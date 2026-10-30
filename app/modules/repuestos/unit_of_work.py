"""Unit of Work del módulo de repuestos."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.repuestos.repository import (
    HistorialPrecioRepository,
    MovimientoStockRepository,
    RepuestoRepository,
    StockRepository,
)


class RepuestosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repuestos = RepuestoRepository(session, Repuesto)
        self.movimientos = MovimientoStockRepository(session, MovimientoStock)
        self.precios = HistorialPrecioRepository(session, HistorialPrecio)
        self.stock = StockRepository(session)


async def get_repuestos_uow(session: AsyncSession = Depends(get_session)) -> RepuestosUnitOfWork:
    return RepuestosUnitOfWork(session)
