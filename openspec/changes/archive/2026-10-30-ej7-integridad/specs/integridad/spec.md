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

### Requirement: Límite de intentos en una consulta
El login SHALL comprobar el límite de intentos (RN-08) antes de cualquier hash, con una sola
consulta sobre `intento_acceso`, contando los fallos del mismo correo desde la misma dirección
que están dentro de la ventana de 60 segundos y son posteriores al último login correcto. Al
llegar a 5 SHALL responder 429 con `Retry-After`.

#### Scenario: Sexto intento
- **WHEN** hay cinco fallos seguidos del mismo correo y la misma dirección
- **THEN** el sexto responde 429 con `Retry-After` sin verificar la contraseña, aunque sea la correcta

#### Scenario: Fallos viejos
- **WHEN** los cinco fallos son de hace más de 60 segundos
- **THEN** el login vuelve a verificar la contraseña y responde 401

#### Scenario: Un éxito reinicia la cuenta
- **WHEN** después de cuatro fallos hay un login correcto y luego cuatro fallos más
- **THEN** el siguiente login correcto responde 200: los fallos anteriores al éxito siguen en la tabla pero no cuentan

#### Scenario: Retry-After
- **WHEN** el más viejo de los cinco fallos de la ventana fue hace 50 segundos
- **THEN** `Retry-After` vale unos 10 segundos
