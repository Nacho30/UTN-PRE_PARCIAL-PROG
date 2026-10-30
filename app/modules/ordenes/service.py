"""Servicio del módulo de órdenes de trabajo (reglas de negocio)."""

from app.core.dependencies import UsuarioActual
from app.core.errores import ErrorConflicto, ErrorNoEncontrado, ErrorPermiso
from app.core.paginacion import Pagina, ParametrosPagina, calcular_paginacion
from app.modules.ordenes.models import (
    EstadoOrdenCodigo,
    HistorialEstadoOrden,
    ItemOrden,
    OrdenTrabajo,
)
from app.modules.ordenes.schemas import (
    EstadoOrdenOut,
    HistorialEstadoOut,
    ItemOrdenOut,
    OrdenClienteResumen,
    OrdenCrear,
    OrdenDetalleOut,
    OrdenResumenOut,
)
from app.modules.ordenes.unit_of_work import OrdenesUnitOfWork
from app.modules.usuarios.models import Rol


class OrdenesService:
    async def mis_ordenes(
        self, uow: OrdenesUnitOfWork, usuario_id: int, params: ParametrosPagina
    ) -> Pagina[OrdenResumenOut]:
        async with uow:
            items, total = await uow.ordenes.get_de_usuario(
                usuario_id, params.page, params.size
            )
            page, size, pages = calcular_paginacion(total, params)
            resumenes = [
                OrdenResumenOut(
                    id=o.id,
                    estado=o.estado,
                    patente=o.vehiculo.patente,
                    total=o.total,
                    creada_en=o.creada_en,
                    mecanico_id=o.mecanico_id,
                )
                for o in items
            ]
            return Pagina[OrdenResumenOut](
                items=resumenes, total=total, page=page, size=size, pages=pages
            )

    def _es_dueno(self, orden: OrdenTrabajo, usuario_id: int) -> bool:
        return orden.vehiculo.cliente.usuario_id == usuario_id

    async def listar_estados(self, uow: OrdenesUnitOfWork) -> list[EstadoOrdenOut]:
        async with uow:
            estados = await uow.estados.list_all()
            return [
                EstadoOrdenOut(
                    codigo=e.codigo,
                    descripcion=e.descripcion,
                    posicion=e.posicion,
                    es_final=e.es_final,
                )
                for e in estados
            ]

    async def listar_ordenes(
        self,
        uow: OrdenesUnitOfWork,
        estado: str | None,
        params: ParametrosPagina,
    ) -> Pagina[OrdenResumenOut]:
        async with uow:
            items, total = await uow.ordenes.list_paginado(
                estado, params.page, params.size
            )
            page, size, pages = calcular_paginacion(total, params)
            resumenes = [
                OrdenResumenOut(
                    id=o.id,  # type: ignore[arg-type]
                    estado=o.estado,
                    patente=o.vehiculo.patente,
                    total=o.total,
                    creada_en=o.creada_en,
                    mecanico_id=o.mecanico_id,
                )
                for o in items
            ]
            return Pagina[OrdenResumenOut](
                items=resumenes,
                total=total,
                page=page,
                size=size,
                pages=pages,
            )

    async def obtener_detalle(
        self, uow: OrdenesUnitOfWork, orden_id: int, actual: UsuarioActual | None = None
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_detalle(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")
            if (
                actual is not None
                and not set(actual.roles).intersection(
                    (Rol.ADMIN, Rol.RECEPCION, Rol.MECANICO)
                )
                and not self._es_dueno(orden, actual.usuario.id)
            ):
                raise ErrorPermiso()
            return self._mapear_detalle(orden)

    def _mapear_detalle(self, orden: OrdenTrabajo) -> OrdenDetalleOut:
        cliente_resumen = OrdenClienteResumen(
            id=orden.vehiculo.cliente.id,  # type: ignore[arg-type]
            nombre=orden.vehiculo.cliente.nombre,
            documento=orden.vehiculo.cliente.documento,
        )

        items_out = [
            ItemOrdenOut(
                repuesto_id=it.repuesto_id,
                codigo=it.repuesto.codigo,
                descripcion=it.repuesto.descripcion,
                cantidad=it.cantidad,
                precio_unitario=it.precio_unitario,
                subtotal=it.precio_unitario * it.cantidad,
            )
            for it in orden.items
        ]

        historial_out = [
            HistorialEstadoOut(
                desde_estado=h.desde_estado,
                hasta_estado=h.hasta_estado,
                usuario_id=h.usuario_id,
                cuando=h.cuando,
            )
            for h in orden.historial
        ]

        return OrdenDetalleOut(
            id=orden.id,  # type: ignore[arg-type]
            estado=orden.estado,
            patente=orden.vehiculo.patente,
            total=orden.total,
            creada_en=orden.creada_en,
            mecanico_id=orden.mecanico_id,
            falla=orden.falla,
            cliente=cliente_resumen,
            items=items_out,
            historial=historial_out,
        )

    async def crear_orden(
        self,
        uow: OrdenesUnitOfWork,
        payload: OrdenCrear,
        usuario_id: int = 3,
    ) -> OrdenDetalleOut:
        async with uow:
            # RN-19: Verificar catálogo de estados
            estado_pendiente = await uow.estados.get_by_codigo(
                EstadoOrdenCodigo.PENDIENTE
            )
            if not estado_pendiente:
                raise ErrorConflicto(
                    "El catálogo de estados está vacío: falta correr seed.py")

            # Verificar vehículo vigente
            vehiculo = await uow.vehiculos.get_by_id(payload.vehiculo_id)
            if not vehiculo:
                raise ErrorConflicto("El vehículo no existe o fue dado de baja")

            # C-10 y RN-10: Verificar repuestos vigentes y copiar precio_unitario.
            # Todos en una sola consulta, no uno por ítem (ejercicio 8).
            repuestos_map = await uow.repuestos.get_vigentes_por_ids(
                [it.repuesto_id for it in payload.items]
            )
            if len(repuestos_map) != len(payload.items):
                raise ErrorConflicto(
                    "Uno o más repuestos no existen o fueron dados de baja"
                )

            total = sum(
                (
                    repuestos_map[it.repuesto_id].precio * it.cantidad
                    for it in payload.items
                ),
                start=0,
            )

            orden = OrdenTrabajo(
                vehiculo_id=payload.vehiculo_id,
                falla=payload.falla,
                estado=EstadoOrdenCodigo.PENDIENTE,
                total=total,
                mecanico_id=None,
            )
            await uow.ordenes.add(orden)

            for item_in in payload.items:
                rep = repuestos_map[item_in.repuesto_id]
                item_entidad = ItemOrden(
                    orden_id=orden.id,  # type: ignore[arg-type]
                    repuesto_id=item_in.repuesto_id,
                    cantidad=item_in.cantidad,
                    precio_unitario=rep.precio,
                )
                await uow.items.add(item_entidad)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,  # type: ignore[arg-type]
                desde_estado=None,
                hasta_estado=EstadoOrdenCodigo.PENDIENTE,
                usuario_id=usuario_id,
            )
            await uow.historial.add(historial)

            return self._mapear_detalle(await uow.ordenes.get_detalle(orden.id))

    async def iniciar_orden(
        self,
        uow: OrdenesUnitOfWork,
        orden_id: int,
        usuario_id: int = 4,
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_by_id(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")

            if orden.estado != EstadoOrdenCodigo.PENDIENTE:
                raise ErrorConflicto(
                    f"La orden no está en estado PENDIENTE (estado actual: {orden.estado})"
                )

            orden.estado = EstadoOrdenCodigo.EN_REPARACION
            orden.mecanico_id = usuario_id
            await uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,  # type: ignore[arg-type]
                desde_estado=EstadoOrdenCodigo.PENDIENTE,
                hasta_estado=EstadoOrdenCodigo.EN_REPARACION,
                usuario_id=usuario_id,
            )
            await uow.historial.add(historial)

            return self._mapear_detalle(await uow.ordenes.get_detalle(orden.id))

    async def terminar_orden(
        self,
        uow: OrdenesUnitOfWork,
        orden_id: int,
        usuario_id: int,
        roles: list[str],
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_detalle(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")

            if Rol.ADMIN not in roles and (
                Rol.MECANICO not in roles or usuario_id != orden.mecanico_id
            ):
                raise ErrorPermiso()

            if orden.estado != EstadoOrdenCodigo.EN_REPARACION:
                raise ErrorConflicto(
                    f"La orden no está en estado EN_REPARACION (estado actual: {orden.estado})"
                )

            # RN-13: Verificar y descontar stock de cada ítem con MovimientoStock.
            # `get_detalle` ya trajo el repuesto de cada ítem (recién leído, con
            # populate_existing): no se vuelve a pedir uno por uno. El UPDATE condicionado
            # de `stock.mover` es el que garantiza el stock; esto sólo da el mensaje claro.
            for it in orden.items:
                rep = it.repuesto
                if rep.borrado_en is not None or rep.stock < it.cantidad:
                    raise ErrorConflicto(
                        f"Stock insuficiente para el repuesto {rep.codigo}"
                    )

                await uow.stock.mover(
                    rep,
                    cantidad=-it.cantidad,
                    motivo=f"Salida por orden #{orden.id}",
                    usuario_id=usuario_id,
                    orden_id=orden.id,
                )

            orden.estado = EstadoOrdenCodigo.TERMINADA
            await uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,  # type: ignore[arg-type]
                desde_estado=EstadoOrdenCodigo.EN_REPARACION,
                hasta_estado=EstadoOrdenCodigo.TERMINADA,
                usuario_id=usuario_id,
            )
            await uow.historial.add(historial)

            return self._mapear_detalle(await uow.ordenes.get_detalle(orden.id))

    async def cancelar_orden(
        self,
        uow: OrdenesUnitOfWork,
        orden_id: int,
        usuario_id: int,
        roles: list[str],
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_detalle(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")

            if not set(roles).intersection(
                (Rol.ADMIN, Rol.RECEPCION)
            ) and not self._es_dueno(orden, usuario_id):
                raise ErrorPermiso()

            if orden.estado != EstadoOrdenCodigo.PENDIENTE:
                raise ErrorConflicto(
                    f"La orden no está en estado PENDIENTE (estado actual: {orden.estado})"
                )

            orden.estado = EstadoOrdenCodigo.CANCELADA
            await uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,  # type: ignore[arg-type]
                desde_estado=EstadoOrdenCodigo.PENDIENTE,
                hasta_estado=EstadoOrdenCodigo.CANCELADA,
                usuario_id=usuario_id,
            )
            await uow.historial.add(historial)

            return self._mapear_detalle(await uow.ordenes.get_detalle(orden.id))
