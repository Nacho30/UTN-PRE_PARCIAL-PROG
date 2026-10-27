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
)


class RepuestosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.repuestos = RepuestoRepository(session, Repuesto)
        self.movimientos = MovimientoStockRepository(session, MovimientoStock)
        self.precios = HistorialPrecioRepository(session, HistorialPrecio)

    async def registrar_movimiento(
        self,
        repuesto: Repuesto,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        orden_id: int | None = None,
    ) -> MovimientoStock:
        """Punto único de escritura de stock con su movimiento (RN-14)."""
        repuesto.stock += cantidad
        mov = MovimientoStock(
            repuesto_id=repuesto.id,  # type: ignore[arg-type]
            orden_id=orden_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        await self.movimientos.add(mov)
        await self.repuestos.update(repuesto)
        return mov


async def get_repuestos_uow(session: AsyncSession = Depends(get_session)) -> RepuestosUnitOfWork:
    return RepuestosUnitOfWork(session)
