"""Rutas del módulo de repuestos."""

from fastapi import APIRouter, Depends, Query, status

from app.core.paginacion import Pagina, ParametrosPagina
from app.core.tipos import IdPath
from app.modules.repuestos.schemas import (
    HistorialPrecioOut,
    MovimientoStockOut,
    ReponerStockIn,
    RepuestoCrear,
    RepuestoPatch,
    RepuestoOut,
)
from app.modules.repuestos.service import RepuestosService
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork, get_repuestos_uow

router = APIRouter(prefix="/repuestos", tags=["repuestos"])
service = RepuestosService()


@router.get("", response_model=Pagina[RepuestoOut])
async def listar_repuestos(
    q: str | None = Query(default=None, description="Búsqueda por descripción"),
    params: ParametrosPagina = Depends(),
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> Pagina[RepuestoOut]:
    return await service.listar_repuestos(uow, q, params)


@router.get("/{id}", response_model=RepuestoOut)
async def obtener_repuesto(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.obtener_repuesto(uow, id)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RepuestoOut)
async def crear_repuesto(
    payload: RepuestoCrear,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    # En ej3, usuario_id por defecto es 1 (admin)
    return await service.crear_repuesto(uow, payload, usuario_id=1)


@router.patch("/{id}", response_model=RepuestoOut)
async def patch_repuesto(
    id: IdPath,
    payload: RepuestoPatch,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.patch_repuesto(uow, id, payload, usuario_id=1)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def baja_repuesto(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> None:
    await service.baja_repuesto(uow, id)


@router.post("/{id}/reponer", response_model=RepuestoOut)
async def reponer_stock(
    id: IdPath,
    payload: ReponerStockIn,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.reponer_stock(uow, id, payload, usuario_id=1)


@router.get("/{id}/movimientos", response_model=list[MovimientoStockOut])
async def listar_movimientos(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> list[MovimientoStockOut]:
    return await service.listar_movimientos(uow, id)


@router.get("/{id}/precios", response_model=list[HistorialPrecioOut])
async def listar_precios(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> list[HistorialPrecioOut]:
    return await service.listar_precios(uow, id)
