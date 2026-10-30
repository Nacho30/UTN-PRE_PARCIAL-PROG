"""Rutas del módulo de repuestos."""

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import UsuarioActual, get_usuario_actual, requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina
from app.core.tipos import IdPath
from app.modules.repuestos.schemas import (
    HistorialPrecioOut,
    MovimientoStockOut,
    ReponerStockIn,
    RepuestoCrear,
    RepuestoOut,
    RepuestoPatch,
)
from app.modules.repuestos.service import RepuestosService
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork, get_repuestos_uow
from app.modules.usuarios.models import Rol

router = APIRouter(
    prefix="/repuestos",
    tags=["repuestos"],
    dependencies=[Depends(requiere_rol(Rol.ADMIN, Rol.RECEPCION, Rol.MECANICO))],
)
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


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RepuestoOut,
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
)
async def crear_repuesto(
    payload: RepuestoCrear,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.crear_repuesto(uow, payload, usuario_id=actual.usuario.id)


@router.patch(
    "/{id}", response_model=RepuestoOut, dependencies=[Depends(requiere_rol(Rol.ADMIN))]
)
async def patch_repuesto(
    id: IdPath,
    payload: RepuestoPatch,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.patch_repuesto(uow, id, payload, usuario_id=actual.usuario.id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
)
async def baja_repuesto(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> None:
    await service.baja_repuesto(uow, id)


@router.post(
    "/{id}/reponer",
    response_model=RepuestoOut,
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
)
async def reponer_stock(
    id: IdPath,
    payload: ReponerStockIn,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> RepuestoOut:
    return await service.reponer_stock(uow, id, payload, usuario_id=actual.usuario.id)


@router.get(
    "/{id}/movimientos",
    response_model=list[MovimientoStockOut],
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
)
async def listar_movimientos(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> list[MovimientoStockOut]:
    return await service.listar_movimientos(uow, id)


@router.get(
    "/{id}/precios",
    response_model=list[HistorialPrecioOut],
    dependencies=[Depends(requiere_rol(Rol.ADMIN))],
)
async def listar_precios(
    id: IdPath,
    uow: RepuestosUnitOfWork = Depends(get_repuestos_uow),
) -> list[HistorialPrecioOut]:
    return await service.listar_precios(uow, id)
