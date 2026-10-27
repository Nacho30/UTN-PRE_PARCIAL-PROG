"""Servicio del módulo de clientes y vehículos (reglas de negocio)."""

from app.core.errores import ErrorConflicto, ErrorNoEncontrado
from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.clientes.schemas import (
    ClienteCrear,
    ClienteDetalleOut,
    ClienteOut,
    VehiculoCrear,
    VehiculoOut,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork


class ClientesService:
    async def crear_cliente(self, uow: ClientesUnitOfWork, payload: ClienteCrear) -> ClienteOut:
        async with uow:
            cliente = Cliente(
                nombre=payload.nombre,
                documento=payload.documento,
                telefono=payload.telefono,
            )
            await uow.clientes.add(cliente)
            return ClienteOut(
                id=cliente.id,  # type: ignore[arg-type]
                usuario_id=cliente.usuario_id,
                nombre=cliente.nombre,
                documento=cliente.documento,
                telefono=cliente.telefono,
            )

    async def obtener_cliente(self, uow: ClientesUnitOfWork, cliente_id: int) -> ClienteDetalleOut:
        async with uow:
            cliente = await uow.clientes.get_detalle(cliente_id)
            if not cliente:
                raise ErrorNoEncontrado(f"No existe el cliente con id {cliente_id}")

            vehiculos_vigentes = [
                VehiculoOut(
                    id=v.id,  # type: ignore[arg-type]
                    cliente_id=v.cliente_id,
                    patente=v.patente,
                    marca=v.marca,
                    modelo=v.modelo,
                    anio=v.anio,
                    borrado_en=v.borrado_en,
                )
                for v in cliente.vehiculos
                if v.borrado_en is None
            ]

            return ClienteDetalleOut(
                id=cliente.id,  # type: ignore[arg-type]
                usuario_id=cliente.usuario_id,
                nombre=cliente.nombre,
                documento=cliente.documento,
                telefono=cliente.telefono,
                vehiculos=vehiculos_vigentes,
            )

    async def crear_vehiculo(
        self,
        uow: ClientesUnitOfWork,
        cliente_id: int,
        payload: VehiculoCrear,
    ) -> VehiculoOut:
        async with uow:
            cliente = await uow.clientes.get_by_id(cliente_id)
            if not cliente:
                raise ErrorNoEncontrado(f"No existe el cliente con id {cliente_id}")

            vehiculo = Vehiculo(
                cliente_id=cliente_id,
                patente=payload.patente,
                marca=payload.marca,
                modelo=payload.modelo,
                anio=payload.anio,
            )
            await uow.vehiculos.add(vehiculo)
            return VehiculoOut(
                id=vehiculo.id,  # type: ignore[arg-type]
                cliente_id=vehiculo.cliente_id,
                patente=vehiculo.patente,
                marca=vehiculo.marca,
                modelo=vehiculo.modelo,
                anio=vehiculo.anio,
                borrado_en=vehiculo.borrado_en,
            )

    async def baja_vehiculo(self, uow: ClientesUnitOfWork, vehiculo_id: int) -> None:
        async with uow:
            vehiculo = await uow.vehiculos.get_by_id(vehiculo_id)
            if not vehiculo:
                raise ErrorNoEncontrado(f"No existe el vehículo con id {vehiculo_id}")

            if await uow.vehiculos.tiene_ordenes_abiertas(vehiculo_id):
                raise ErrorConflicto("No se puede dar de baja un vehículo con órdenes de trabajo abiertas")

            await uow.vehiculos.soft_delete(vehiculo)
