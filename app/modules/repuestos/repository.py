"""Repositorios del módulo de repuestos."""

from sqlalchemy import func, select

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
