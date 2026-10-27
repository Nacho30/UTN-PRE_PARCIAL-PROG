## ADDED Requirements

### Requirement: Tablas de sólo agregado
`historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto` SHALL rechazar
cualquier `UPDATE` o `DELETE`, venga de donde venga, mediante un disparador instalado por una
migración escrita a mano (RN-15).

#### Scenario: UPDATE desde psql
- **WHEN** en `psql` se ejecuta `UPDATE movimiento_stock SET cantidad = 99`
- **THEN** la base lo rechaza con «movimiento_stock es de sólo agregado: no se permite UPDATE»

#### Scenario: INSERT
- **WHEN** se agrega una fila nueva en cualquiera de las tres tablas
- **THEN** la base la acepta

### Requirement: Intento de acceso en su propia transacción
Cada intento de login, correcto o fallido, SHALL anotarse en `intento_acceso` desde una
sesión y una transacción propias, que se confirman siempre. Es la única escritura del sistema
que no comparte la transacción de su petición.

#### Scenario: Login fallido
- **WHEN** un login falla y la petición responde 401
- **THEN** la fila del intento con `exito = false` queda guardada
