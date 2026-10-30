"""Servicio del módulo de repuestos (reglas de negocio)."""

from app.core.errores import ErrorNoEncontrado
from app.core.paginacion import Pagina, ParametrosPagina, calcular_paginacion
from app.modules.repuestos.models import HistorialPrecio, Repuesto
from app.modules.repuestos.schemas import (
    HistorialPrecioOut,
    MovimientoStockOut,
    ReponerStockIn,
    RepuestoCrear,
    RepuestoPatch,
    RepuestoOut,
)
from app.modules.repuestos.unit_of_work import RepuestosUnitOfWork


class RepuestosService:
    async def listar_repuestos(
        self,
        uow: RepuestosUnitOfWork,
        q: str | None,
        params: ParametrosPagina,
    ) -> Pagina[RepuestoOut]:
        async with uow:
            items, total = await uow.repuestos.list_paginado(q, params.page, params.size)
            page, size, pages = calcular_paginacion(total, params)
            items_out = [
                RepuestoOut(
                    id=it.id,  # type: ignore[arg-type]
                    codigo=it.codigo,
                    descripcion=it.descripcion,
                    precio=it.precio,
                    stock=it.stock,
                    borrado_en=it.borrado_en,
                )
                for it in items
            ]
            return Pagina[RepuestoOut](
                items=items_out,
                total=total,
                page=page,
                size=size,
                pages=pages,
            )

    async def obtener_repuesto(self, uow: RepuestosUnitOfWork, repuesto_id: int) -> RepuestoOut:
        async with uow:
            repuesto = await uow.repuestos.get_by_id(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")
            return RepuestoOut(
                id=repuesto.id,  # type: ignore[arg-type]
                codigo=repuesto.codigo,
                descripcion=repuesto.descripcion,
                precio=repuesto.precio,
                stock=repuesto.stock,
                borrado_en=repuesto.borrado_en,
            )

    async def crear_repuesto(
        self,
        uow: RepuestosUnitOfWork,
        payload: RepuestoCrear,
        usuario_id: int = 1,
    ) -> RepuestoOut:
        async with uow:
            repuesto = Repuesto(
                codigo=payload.codigo,
                descripcion=payload.descripcion,
                precio=payload.precio,
                stock=0,
            )
            await uow.repuestos.add(repuesto)

            if payload.stock_inicial > 0:
                await uow.stock.mover(
                    repuesto,
                    cantidad=payload.stock_inicial,
                    motivo="Stock inicial",
                    usuario_id=usuario_id,
                )

            return RepuestoOut(
                id=repuesto.id,  # type: ignore[arg-type]
                codigo=repuesto.codigo,
                descripcion=repuesto.descripcion,
                precio=repuesto.precio,
                stock=repuesto.stock,
                borrado_en=repuesto.borrado_en,
            )

    async def patch_repuesto(
        self,
        uow: RepuestosUnitOfWork,
        repuesto_id: int,
        payload: RepuestoPatch,
        usuario_id: int = 1,
    ) -> RepuestoOut:
        async with uow:
            repuesto = await uow.repuestos.get_by_id(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")

            cambios = payload.model_dump(exclude_unset=True)

            if "precio" in cambios:
                nuevo_precio = cambios["precio"]
                if nuevo_precio != repuesto.precio:
                    historial = HistorialPrecio(
                        repuesto_id=repuesto.id,  # type: ignore[arg-type]
                        usuario_id=usuario_id,
                        precio_anterior=repuesto.precio,
                        precio_nuevo=nuevo_precio,
                    )
                    await self._guardar_historial_precio(uow, historial)
                    repuesto.precio = nuevo_precio

            if "descripcion" in cambios:
                repuesto.descripcion = cambios["descripcion"]

            await uow.repuestos.update(repuesto)
            return RepuestoOut(
                id=repuesto.id,  # type: ignore[arg-type]
                codigo=repuesto.codigo,
                descripcion=repuesto.descripcion,
                precio=repuesto.precio,
                stock=repuesto.stock,
                borrado_en=repuesto.borrado_en,
            )

    async def _guardar_historial_precio(
        self,
        uow: RepuestosUnitOfWork,
        historial: HistorialPrecio,
    ) -> None:
        await uow.precios.add(historial)

    async def baja_repuesto(self, uow: RepuestosUnitOfWork, repuesto_id: int) -> None:
        async with uow:
            repuesto = await uow.repuestos.get_by_id(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")
            await uow.repuestos.soft_delete(repuesto)

    async def reponer_stock(
        self,
        uow: RepuestosUnitOfWork,
        repuesto_id: int,
        payload: ReponerStockIn,
        usuario_id: int = 1,
    ) -> RepuestoOut:
        async with uow:
            repuesto = await uow.repuestos.get_by_id(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")

            await uow.stock.mover(
                repuesto,
                cantidad=payload.cantidad,
                motivo=payload.motivo,
                usuario_id=usuario_id,
            )
            return RepuestoOut(
                id=repuesto.id,  # type: ignore[arg-type]
                codigo=repuesto.codigo,
                descripcion=repuesto.descripcion,
                precio=repuesto.precio,
                stock=repuesto.stock,
                borrado_en=repuesto.borrado_en,
            )

    async def listar_movimientos(
        self,
        uow: RepuestosUnitOfWork,
        repuesto_id: int,
    ) -> list[MovimientoStockOut]:
        async with uow:
            repuesto = await uow.repuestos.get_by_id_including_deleted(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")

            movs = await uow.movimientos.list_by_repuesto(repuesto_id)
            return [
                MovimientoStockOut(
                    id=m.id,  # type: ignore[arg-type]
                    repuesto_id=m.repuesto_id,
                    orden_id=m.orden_id,
                    usuario_id=m.usuario_id,
                    cantidad=m.cantidad,
                    motivo=m.motivo,
                    cuando=m.cuando,
                )
                for m in movs
            ]

    async def listar_precios(
        self,
        uow: RepuestosUnitOfWork,
        repuesto_id: int,
    ) -> list[HistorialPrecioOut]:
        async with uow:
            repuesto = await uow.repuestos.get_by_id_including_deleted(repuesto_id)
            if not repuesto:
                raise ErrorNoEncontrado(f"No existe el repuesto con id {repuesto_id}")

            precios = await uow.precios.list_by_repuesto(repuesto_id)
            return [
                HistorialPrecioOut(
                    id=p.id,  # type: ignore[arg-type]
                    repuesto_id=p.repuesto_id,
                    usuario_id=p.usuario_id,
                    precio_anterior=p.precio_anterior,
                    precio_nuevo=p.precio_nuevo,
                    cuando=p.cuando,
                )
                for p in precios
            ]
