"""Repositorios del módulo de clientes y vehículos."""

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, OrdenTrabajo


class ClienteRepository(BaseRepository[Cliente]):
    async def get_detalle(self, id: int) -> Cliente | None:
        stmt = (
            select(Cliente)
            .where(Cliente.id == id)
            .options(selectinload(Cliente.vehiculos))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_documento(self, documento: str) -> Cliente | None:
        stmt = select(Cliente).where(Cliente.documento == documento)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class VehiculoRepository(SoftDeleteRepository[Vehiculo]):
    async def get_de_usuario(self, usuario_id: int) -> list[Vehiculo]:
        stmt = (
            select(Vehiculo)
            .join(Cliente)
            .where(Cliente.usuario_id == usuario_id, Vehiculo.borrado_en.is_(None))
            .order_by(Vehiculo.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_patente_vigente(self, patente: str) -> Vehiculo | None:
        stmt = select(Vehiculo).where(
            Vehiculo.patente == patente,
            Vehiculo.borrado_en.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def tiene_ordenes_abiertas(self, vehiculo_id: int) -> bool:
        """Comprueba si el vehículo tiene órdenes no finalizadas (RN-16)."""
        stmt = (
            select(func.count())
            .select_from(OrdenTrabajo)
            .join(EstadoOrden, OrdenTrabajo.estado == EstadoOrden.codigo)
            .where(
                OrdenTrabajo.vehiculo_id == vehiculo_id,
                EstadoOrden.es_final.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
