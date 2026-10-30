"""Repositorios del módulo de repuestos."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.errores import ErrorConflicto

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto


class RepuestoRepository(SoftDeleteRepository[Repuesto]):
    async def list_paginado(
        self,
        q: str | None,
        page: int,
        size: int,
    ) -> tuple[list[Repuesto], int]:
        condiciones = [Repuesto.borrado_en.is_(None)]
        if q:
            # Escapamos los comodines para asegurar búsqueda literal con parámetros ligados
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            condiciones.append(Repuesto.descripcion.ilike(f"%{escaped}%", escape="\\"))

        stmt_count = select(func.count()).select_from(Repuesto).where(*condiciones)
        total = (await self.session.execute(stmt_count)).scalar_one()

        stmt_items = (
            select(Repuesto)
            .where(*condiciones)
            .order_by(Repuesto.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        items = list((await self.session.execute(stmt_items)).scalars().all())
        return items, total

    async def get_vigentes_por_ids(self, ids: list[int]) -> dict[int, Repuesto]:
        """Los repuestos vigentes de esa lista, en UNA consulta (`WHERE id IN (...)`).

        Lo usa el alta de una orden: pedirlos de a uno con `get_by_id` haría una consulta
        por ítem (N+1). Los ids que falten en el diccionario no existen o están de baja.
        """
        if not ids:
            return {}
        stmt = select(Repuesto).where(Repuesto.id.in_(ids), Repuesto.borrado_en.is_(None))
        return {r.id: r for r in (await self.session.execute(stmt)).scalars().all()}

    async def get_by_codigo_vigente(self, codigo: str) -> Repuesto | None:
        stmt = select(Repuesto).where(
            Repuesto.codigo == codigo,
            Repuesto.borrado_en.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    async def list_by_repuesto(self, repuesto_id: int) -> list[MovimientoStock]:
        stmt = (
            select(MovimientoStock)
            .where(MovimientoStock.repuesto_id == repuesto_id)
            .order_by(MovimientoStock.cuando.desc(), MovimientoStock.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class HistorialPrecioRepository(BaseRepository[HistorialPrecio]):
    async def list_by_repuesto(self, repuesto_id: int) -> list[HistorialPrecio]:
        stmt = (
            select(HistorialPrecio)
            .where(HistorialPrecio.repuesto_id == repuesto_id)
            .order_by(HistorialPrecio.cuando.desc(), HistorialPrecio.id.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class StockRepository:
    """Único punto de escritura de stock; el UoW confirma stock y movimiento juntos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def mover(
        self,
        repuesto: Repuesto,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        orden_id: int | None = None,
    ) -> MovimientoStock:
        if cantidad == 0:
            raise ErrorConflicto("El movimiento de stock no puede ser cero")
        nuevo_stock = (await self.session.execute(
            update(Repuesto)
            .where(
                Repuesto.id == repuesto.id,
                Repuesto.borrado_en.is_(None),
                Repuesto.stock + cantidad >= 0,
            )
            .values(stock=Repuesto.stock + cantidad)
            .returning(Repuesto.stock)
            .execution_options(synchronize_session=False)
        )).scalar_one_or_none()
        if nuevo_stock is None:
            raise ErrorConflicto(
                f"Stock insuficiente o repuesto no vigente: {repuesto.codigo}")
        # El UPDATE ya persistió este atributo; evitar otro UPDATE del ORM al hacer flush.
        set_committed_value(repuesto, "stock", nuevo_stock)
        movimiento = MovimientoStock(
            repuesto_id=repuesto.id,
            orden_id=orden_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        await MovimientoStockRepository(self.session, MovimientoStock).add(movimiento)
        return movimiento
