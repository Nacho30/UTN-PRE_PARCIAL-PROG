"""Rutas del módulo de clientes y vehículos."""

from fastapi import APIRouter, Depends, status

from app.core.tipos import IdPath
from app.modules.clientes.schemas import (
    ClienteCrear,
    ClienteDetalleOut,
    ClienteOut,
    VehiculoCrear,
    VehiculoOut,
)
from app.modules.clientes.service import ClientesService
from app.modules.clientes.unit_of_work import ClientesUnitOfWork, get_clientes_uow

router = APIRouter(tags=["clientes"])
service = ClientesService()


@router.post("/clientes", status_code=status.HTTP_201_CREATED, response_model=ClienteOut)
async def crear_cliente(
    payload: ClienteCrear,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> ClienteOut:
    return await service.crear_cliente(uow, payload)


@router.get("/clientes/{id}", response_model=ClienteDetalleOut)
async def obtener_cliente(
    id: IdPath,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> ClienteDetalleOut:
    return await service.obtener_cliente(uow, id)


@router.post("/clientes/{id}/vehiculos", status_code=status.HTTP_201_CREATED, response_model=VehiculoOut)
async def crear_vehiculo(
    id: IdPath,
    payload: VehiculoCrear,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> VehiculoOut:
    return await service.crear_vehiculo(uow, id, payload)


@router.delete("/vehiculos/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def baja_vehiculo(
    id: IdPath,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> None:
    await service.baja_vehiculo(uow, id)
