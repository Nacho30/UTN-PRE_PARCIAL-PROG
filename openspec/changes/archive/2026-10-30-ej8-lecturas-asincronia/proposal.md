# Ejercicio 8 · Lecturas sin N+1 y asincronía

## Why
Una lectura que dispara una consulta por cada ítem crece con los datos y, en un motor
asincrónico, la carga perezosa directamente falla (sección 3.8). Y una llamada bloqueante en un
handler `async def` frena a todos los clientes (sección 3.6).

## What Changes
- Precarga declarada en el repositorio (`selectinload` / `joinedload`).
- `OrdenTrabajoRepository.get_detalle`: número fijo de consultas (orden + vehículo + cliente en
  un JOIN; ítems; repuestos; historial), sin importar la cantidad de ítems.
- Todas las relaciones con `lazy="raise_on_sql"`: una lectura no precargada falla en vez de
  esconder una consulta.
- Todos los handlers `async def`; bcrypt en `to_thread`.
- Aviso al cliente con `BackgroundTasks` al terminar una orden: `await asyncio.sleep(0.5)` y un
  mensaje en el registro. Se agenda sólo después de que el servicio confirmó.
- `SQL_ECHO=true` muestra las consultas en la consola (evidencia de C-15).

## Impact
- Capabilities: `lecturas`.
- Archivos: `app/modules/ordenes/{repository,router,avisos}.py`.
