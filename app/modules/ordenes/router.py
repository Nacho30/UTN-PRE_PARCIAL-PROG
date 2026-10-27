"""Rutas del módulo de órdenes de trabajo y catálogo de estados."""

from fastapi import APIRouter, Depends, Query, status

from app.core.paginacion import Pagina, ParametrosPagina
from app.core.tipos import IdPath
from app.modules.ordenes.models import EstadoOrdenCodigo
from app.modules.ordenes.schemas import (
    EstadoOrdenOut,
    OrdenCrear,
    OrdenDetalleOut,
    OrdenResumenOut,
)
from app.modules.ordenes.service import OrdenesService
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork, get_ordenes_uow

router = APIRouter(tags=["ordenes"])
service = OrdenesService()


@router.get("/estados-orden", response_model=list[EstadoOrdenOut])
async def listar_estados(
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> list[EstadoOrdenOut]:
    return await service.listar_estados(uow)


@router.post("/ordenes", status_code=status.HTTP_201_CREATED, response_model=OrdenDetalleOut)
async def crear_orden(
    payload: OrdenCrear,
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    # En ej3, usuario_id por defecto es 3 (recepción)
    return await service.crear_orden(uow, payload, usuario_id=3)


@router.get("/ordenes", response_model=Pagina[OrdenResumenOut])
async def listar_ordenes(
    estado: EstadoOrdenCodigo | None = Query(default=None, description="Filtrar por código de estado"),
    params: ParametrosPagina = Depends(),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> Pagina[OrdenResumenOut]:
    return await service.listar_ordenes(uow, estado, params)


@router.get("/ordenes/{id}", response_model=OrdenDetalleOut)
async def obtener_orden(
    id: IdPath,
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    return await service.obtener_detalle(uow, id)


@router.post("/ordenes/{id}/iniciar", response_model=OrdenDetalleOut)
async def iniciar_orden(
    id: IdPath,
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    # En ej3, usuario_id por defecto es 4 (mecánico)
    return await service.iniciar_orden(uow, id, usuario_id=4)


@router.post("/ordenes/{id}/terminar", response_model=OrdenDetalleOut)
async def terminar_orden(
    id: IdPath,
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    # En ej3, usuario_id por defecto es 4 (mecánico)
    return await service.terminar_orden(uow, id, usuario_id=4)


@router.post("/ordenes/{id}/cancelar", response_model=OrdenDetalleOut)
async def cancelar_orden(
    id: IdPath,
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    # En ej3, usuario_id por defecto es 3 (recepción)
    return await service.cancelar_orden(uow, id, usuario_id=3)
