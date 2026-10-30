# persistencia Specification

## Purpose
Garantizar operaciones de negocio atómicas mediante repositorios sin commit, Unit of Work inyectados y un único punto de escritura de stock.

## Requirements

### Requirement: Ningún repositorio confirma
`BaseRepository[T]` SHALL recibir en su constructor la sesión y la clase del modelo. `add` y
`update` SHALL hacer `flush()` y MUST NOT hacer `commit()`.

#### Scenario: Error de unicidad en el flush
- **WHEN** `add` choca con un índice único
- **THEN** el `IntegrityError` sale en el `flush`, dentro del bloque del UoW, y el UoW revierte

### Requirement: Unit of Work
El `UnitOfWork` base SHALL ser un gestor de contexto asincrónico que confirma al salir del
bloque, revierte si se sale con una excepción y MUST NOT cerrar la sesión. El router SHALL
construirlo con una dependencia y el servicio SHALL abrirlo con `async with` sin construirlo.

#### Scenario: Fallo en el medio
- **WHEN** al terminar la orden 2 el segundo de tres pasos falla
- **THEN** no queda ninguna de las escrituras del bloque

### Requirement: Stock en un único punto
El stock de un repuesto SHALL cambiar sólo mediante `StockRepository.mover`, que escribe el
stock y su movimiento en la misma transacción (RN-14).

#### Scenario: Stock insuficiente
- **WHEN** se termina la orden 2, que pide 4 bujías con 2 en stock
- **THEN** responde 409 y el estado, el stock, los movimientos y el historial quedan como estaban

### Requirement: Catálogo de sólo lectura
El catálogo SHALL tener un repositorio propio que no hereda de `BaseRepository` y no ofrece
`add`, `update` ni `delete`.

#### Scenario: Catálogo vacío
- **WHEN** `estado_orden` no tiene filas y se crea una orden
- **THEN** responde 409 «El catálogo de estados está vacío: falta correr seed.py»

### Requirement: Cambio de precio con historial
Cada cambio de precio SHALL dejar una línea en `historial_precio_repuesto` en la misma
transacción; un PATCH que no cambia el precio no deja línea (RN-20).

#### Scenario: PATCH de sólo descripción
- **WHEN** después de cambiar el precio se hace un PATCH que sólo cambia la descripción
- **THEN** `/repuestos/{id}/precios` sigue con una sola línea nueva
