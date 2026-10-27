"""Unit of Work del módulo de clientes y vehículos."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.repository import ClienteRepository, VehiculoRepository


class ClientesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session, Cliente)
        self.vehiculos = VehiculoRepository(session, Vehiculo)


async def get_clientes_uow(session: AsyncSession = Depends(get_session)) -> ClientesUnitOfWork:
    return ClientesUnitOfWork(session)
