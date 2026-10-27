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
