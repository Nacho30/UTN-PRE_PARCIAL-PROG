# Tareas · Ejercicio 6

## 1. Jerarquías
- [x] 1.1 `BaseRepository[T]` con la clase del modelo en el constructor
- [x] 1.2 `SoftDeleteRepository[T]` con filtro, `get_by_id_including_deleted` y `soft_delete`
- [x] 1.3 `UnitOfWork` base asincrónico (commit / rollback, sin cerrar la sesión)

## 2. Por módulo
- [x] 2.1 `usuarios`: repos de Usuario, AsignacionRol, EventoSeguridad, IntentoAcceso; `UsuariosUnitOfWork`, `AccesoUnitOfWork`
- [x] 2.2 `clientes`: repos de Cliente y Vehiculo; `ClientesUnitOfWork`
- [x] 2.3 `repuestos`: repos de Repuesto, MovimientoStock, HistorialPrecio y `StockRepository`; `RepuestosUnitOfWork`
- [x] 2.4 `ordenes`: `EstadoOrdenRepository` (sólo lectura), OrdenTrabajo, ItemOrden, HistorialEstadoOrden; `OrdenesUnitOfWork`

## 3. Operaciones de varias escrituras
- [x] 3.1 RN-02 registro en un bloque
- [x] 3.2 RN-13 terminar orden en un bloque
- [x] 3.3 RN-20 cambio de precio + historial en un bloque
- [x] 3.4 Stock escrito sólo desde `StockRepository.mover` (alta, reposición, terminación)
