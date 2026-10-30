## ADDED Requirements

### Requirement: Detalle con consultas fijas
El detalle de una orden (vehículo, cliente, ítems, repuesto de cada ítem e historial) SHALL
resolverse con un número fijo de consultas que no crece con la cantidad de ítems.

#### Scenario: Dos contra cuatro ítems
- **WHEN** con `SQL_ECHO=true` se pide el detalle de una orden con 2 ítems y de otra con 4
- **THEN** la consola muestra la misma cantidad de consultas

### Requirement: Sin carga perezosa
Ninguna lectura SHALL depender de la carga perezosa: toda relación que se lee se precarga en el
repositorio.

#### Scenario: Relación no precargada
- **WHEN** el código accede a una relación que el repositorio no precargó
- **THEN** SQLAlchemy lanza un error (`raise_on_sql`) en lugar de consultar en silencio

### Requirement: Aviso en segundo plano
Al terminar una orden SHALL agendarse con `BackgroundTasks` un aviso al cliente, simulado con
`await asyncio.sleep(0.5)` y un mensaje en el registro, que corre después de enviar la
respuesta y sólo si la operación se confirmó.

#### Scenario: Terminación fallida
- **WHEN** terminar la orden responde 409
- **THEN** no se agenda ningún aviso

### Requirement: Escrituras de órdenes sin lecturas por ítem
Crear y terminar una orden SHALL leer los repuestos de todos sus ítems con un número fijo de
consultas: las lecturas no crecen con la cantidad de ítems (las escrituras sí: un movimiento
por salida).

#### Scenario: Alta con 2 y con 4 ítems
- **WHEN** se crea una orden con 2 ítems y otra con 4
- **THEN** las dos peticiones hacen la misma cantidad de `SELECT`

### Requirement: Todos los handlers asincrónicos
Todos los handlers SHALL ser `async def` y ninguno SHALL ejecutar una llamada bloqueante; bcrypt
corre en `to_thread`.

#### Scenario: Recorrido de rutas
- **WHEN** se recorren las rutas de la aplicación
- **THEN** todas tienen un endpoint corrutina

### Requirement: Aviso sólo tras confirmar y después de responder
El aviso SHALL agendarse sólo si la terminación se confirmó y SHALL correr después de enviar
la respuesta.

#### Scenario: Commit fallido
- **WHEN** el commit de la terminación falla
- **THEN** la respuesta es 500 sin traza y no se agenda ningún aviso

#### Scenario: Orden de los eventos
- **WHEN** la terminación se confirma
- **THEN** el aviso arranca cuando la respuesta ya salió completa
