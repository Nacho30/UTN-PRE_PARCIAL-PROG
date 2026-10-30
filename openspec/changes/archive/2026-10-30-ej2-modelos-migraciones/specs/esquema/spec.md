## ADDED Requirements

### Requirement: Unicidad garantizada por la base
El correo de un usuario, el documento de un cliente y el `usuario_id` de un cliente SHALL ser
UNIQUE. La patente de un vehículo y el código de un repuesto SHALL ser únicos sólo entre las
filas con `borrado_en IS NULL`, mediante índices únicos parciales. Un usuario SHALL tener a lo
sumo una asignación abierta por rol (`revocada_en IS NULL`).

#### Scenario: Patente de un vehículo dado de baja
- **WHEN** un vehículo con patente `AB123CD` está dado de baja y se registra otro con la misma patente
- **THEN** la base acepta la fila nueva

#### Scenario: Dos patentes vigentes iguales
- **WHEN** se intenta guardar un segundo vehículo vigente con la misma patente
- **THEN** la base rechaza la escritura con `ux_vehiculo_patente_vigente`

### Requirement: Catálogo de estados con clave foránea
`estado_orden` SHALL ser una tabla de referencia con `codigo` como clave primaria y
`posicion` UNIQUE. `orden_trabajo.estado`, `historial_estado_orden.desde_estado` y
`historial_estado_orden.hasta_estado` SHALL ser claves foráneas a `estado_orden.codigo`.
Las migraciones SHALL crear la tabla vacía.

#### Scenario: Estado inexistente
- **WHEN** se inserta una orden con `estado = 'INVENTADO'`
- **THEN** la base la rechaza por la clave foránea

### Requirement: Comprobaciones de dominio en la base
La base SHALL imponer: `vehiculo.anio BETWEEN 1950 AND 2100`; `repuesto.precio > 0`;
`repuesto.stock >= 0`; `orden_trabajo.total >= 0`; `item_orden.cantidad > 0`;
`item_orden.precio_unitario > 0`; `UNIQUE (orden_id, repuesto_id)`;
`movimiento_stock.cantidad <> 0`; `historial_precio_repuesto.precio_nuevo > 0` y
`precio_nuevo <> precio_anterior`; `asignacion_rol.rol IN (ADMIN, RECEPCION, MECANICO, CLIENTE)`.

#### Scenario: Stock negativo
- **WHEN** una escritura dejaría `repuesto.stock` en -1
- **THEN** la base la rechaza con `ck_repuesto_stock_no_negativo`

### Requirement: Esquema sólo con Alembic
El esquema SHALL crearse exclusivamente con Alembic y la plantilla asincrónica; la aplicación
MUST NOT usar `create_all`. Deben existir dos migraciones: la primera autogenerada con todas
las tablas y la segunda escrita a mano con el disparador de sólo agregado.

#### Scenario: Ida, vuelta e ida
- **WHEN** sobre una base vacía se corre `alembic upgrade head`, `alembic downgrade base` y otra vez `alembic upgrade head`
- **THEN** los tres comandos terminan sin errores
