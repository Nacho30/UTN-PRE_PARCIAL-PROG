"""Rutas del módulo de órdenes de trabajo y catálogo de estados."""

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from app.core.dependencies import UsuarioActual, get_usuario_actual, requiere_rol
from app.core.paginacion import Pagina, ParametrosPagina
from app.core.tipos import IdPath
from app.modules.ordenes.avisos import avisar_cliente
from app.modules.ordenes.models import EstadoOrdenCodigo
from app.modules.ordenes.schemas import (
    EstadoOrdenOut,
    OrdenCrear,
    OrdenDetalleOut,
    OrdenResumenOut,
)
from app.modules.ordenes.service import OrdenesService
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork, get_ordenes_uow
from app.modules.usuarios.models import Rol

router = APIRouter(tags=["ordenes"])
service = OrdenesService()


@router.get("/estados-orden", response_model=list[EstadoOrdenOut])
async def listar_estados(
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> list[EstadoOrdenOut]:
    return await service.listar_estados(uow)


@router.post(
    "/ordenes",
    status_code=status.HTTP_201_CREATED,
    response_model=OrdenDetalleOut,
    dependencies=[Depends(requiere_rol(Rol.ADMIN, Rol.RECEPCION))],
)
async def crear_orden(
    payload: OrdenCrear,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    return await service.crear_orden(uow, payload, usuario_id=actual.usuario.id)


@router.get(
    "/ordenes",
    response_model=Pagina[OrdenResumenOut],
    dependencies=[Depends(requiere_rol(Rol.ADMIN, Rol.RECEPCION, Rol.MECANICO))],
)
async def listar_ordenes(
    estado: EstadoOrdenCodigo | None = Query(
        default=None, description="Filtrar por código de estado"
    ),
    params: ParametrosPagina = Depends(),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> Pagina[OrdenResumenOut]:
    return await service.listar_ordenes(uow, estado, params)


@router.get("/ordenes/{id}", response_model=OrdenDetalleOut)
async def obtener_orden(
    id: IdPath,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    return await service.obtener_detalle(uow, id, actual)


@router.post(
    "/ordenes/{id}/iniciar",
    response_model=OrdenDetalleOut,
    dependencies=[Depends(requiere_rol(Rol.MECANICO))],
)
async def iniciar_orden(
    id: IdPath,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    return await service.iniciar_orden(uow, id, usuario_id=actual.usuario.id)


@router.post("/ordenes/{id}/terminar", response_model=OrdenDetalleOut)
async def terminar_orden(
    id: IdPath,
    background_tasks: BackgroundTasks,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    detalle = await service.terminar_orden(
        uow, id, usuario_id=actual.usuario.id, roles=actual.roles
    )
    # Llegar a esta línea quiere decir que el servicio salió de su `async with uow` sin
    # excepción: la terminación YA se confirmó. Si falló (403, 409, o el commit), la
    # excepción salta esta línea y no se agenda nada. El aviso corre después de enviar
    # la respuesta, con datos sueltos y no con objetos del ORM.
    background_tasks.add_task(
        avisar_cliente,
        orden_id=detalle.id,
        cliente=detalle.cliente.nombre,
        patente=detalle.patente,
    )
    return detalle


@router.post("/ordenes/{id}/cancelar", response_model=OrdenDetalleOut)
async def cancelar_orden(
    id: IdPath,
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
) -> OrdenDetalleOut:
    return await service.cancelar_orden(
        uow, id, usuario_id=actual.usuario.id, roles=actual.roles
    )


@router.get("/mis-ordenes", response_model=Pagina[OrdenResumenOut])
async def mis_ordenes(
    params: ParametrosPagina = Depends(),
    actual: UsuarioActual = Depends(get_usuario_actual),
    uow: OrdenesUnitOfWork = Depends(get_ordenes_uow),
):
    return await service.mis_ordenes(uow, actual.usuario.id, params)
