"""Servicio del módulo de órdenes de trabajo (reglas de negocio)."""

from app.core.errores import ErrorConflicto, ErrorNoEncontrado
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
from app.modules.repuestos.models import MovimientoStock


class OrdenesService:
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
            items, total = await uow.ordenes.list_paginado(estado, params.page, params.size)
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

    async def obtener_detalle(self, uow: OrdenesUnitOfWork, orden_id: int) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_detalle(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")
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
            estado_pendiente = await uow.estados.get_by_codigo(EstadoOrdenCodigo.PENDIENTE)
            if not estado_pendiente:
                raise ErrorConflicto("El catálogo de estados de orden no está cargado")

            # Verificar vehículo vigente
            vehiculo = await uow.vehiculos.get_by_id(payload.vehiculo_id)
            if not vehiculo:
                raise ErrorConflicto("El vehículo no existe o fue dado de baja")

            # C-10 y RN-10: Verificar repuestos vigentes y copiar precio_unitario
            repuestos_map = {}
            for item_in in payload.items:
                rep = await uow.repuestos.get_by_id(item_in.repuesto_id)
                if not rep:
                    raise ErrorConflicto("Uno o más repuestos no existen o fueron dados de baja")
                repuestos_map[item_in.repuesto_id] = rep

            total = sum(
                (repuestos_map[it.repuesto_id].precio * it.cantidad for it in payload.items),
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

            return await self.obtener_detalle(uow, orden.id)  # type: ignore[arg-type]

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

            return await self.obtener_detalle(uow, orden.id)  # type: ignore[arg-type]

    async def terminar_orden(
        self,
        uow: OrdenesUnitOfWork,
        orden_id: int,
        usuario_id: int = 4,
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_detalle(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")

            if orden.estado != EstadoOrdenCodigo.EN_REPARACION:
                raise ErrorConflicto(
                    f"La orden no está en estado EN_REPARACION (estado actual: {orden.estado})"
                )

            # RN-13: Verificar y descontar stock de cada ítem con MovimientoStock
            for it in orden.items:
                rep = await uow.repuestos.get_by_id(it.repuesto_id)
                if not rep or rep.stock < it.cantidad:
                    codigo = it.repuesto.codigo if it.repuesto else str(it.repuesto_id)
                    raise ErrorConflicto(
                        f"Stock insuficiente para el repuesto {codigo}"
                    )

                rep.stock -= it.cantidad
                mov = MovimientoStock(
                    repuesto_id=rep.id,  # type: ignore[arg-type]
                    orden_id=orden.id,
                    usuario_id=usuario_id,
                    cantidad=-it.cantidad,
                    motivo=f"Salida por orden #{orden.id}",
                )
                await uow.movimientos.add(mov)
                await uow.repuestos.update(rep)

            orden.estado = EstadoOrdenCodigo.TERMINADA
            await uow.ordenes.update(orden)

            historial = HistorialEstadoOrden(
                orden_id=orden.id,  # type: ignore[arg-type]
                desde_estado=EstadoOrdenCodigo.EN_REPARACION,
                hasta_estado=EstadoOrdenCodigo.TERMINADA,
                usuario_id=usuario_id,
            )
            await uow.historial.add(historial)

            return await self.obtener_detalle(uow, orden.id)  # type: ignore[arg-type]

    async def cancelar_orden(
        self,
        uow: OrdenesUnitOfWork,
        orden_id: int,
        usuario_id: int = 3,
    ) -> OrdenDetalleOut:
        async with uow:
            orden = await uow.ordenes.get_by_id(orden_id)
            if not orden:
                raise ErrorNoEncontrado(f"No existe la orden con id {orden_id}")

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

            return await self.obtener_detalle(uow, orden.id)  # type: ignore[arg-type]
