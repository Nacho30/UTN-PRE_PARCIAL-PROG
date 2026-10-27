# Ejercicio 6 · Repositorios y Unit of Work

## Why
Una operación de negocio con varias escrituras (registro, terminar una orden, cambiar un
precio) tiene que quedar entera o no quedar. Si cada repositorio confirmara lo suyo, un fallo
en el medio dejaría datos a medias.

## What Changes
- `BaseRepository[T]` recibe la sesión y la clase del modelo; ofrece `get_by_id`, `get_all`,
  `count`, `add`, `update`, `delete`. `add` y `update` hacen `flush()`, nunca `commit()`.
- `SoftDeleteRepository[T]` filtra los dados de baja y agrega
  `get_by_id_including_deleted` y `soft_delete`.
- Un repositorio por entidad, con métodos nombrados por lo que traen y la precarga declarada
  adentro del método.
- `EstadoOrdenRepository` de sólo lectura, sin heredar de `BaseRepository`.
- `StockRepository.mover(...)`: el único punto que escribe `repuesto.stock` (RN-14), con un
  `UPDATE ... WHERE stock + :cantidad >= 0` y su `movimiento_stock`.
- `UnitOfWork` base: gestor de contexto asincrónico que confirma al salir, revierte con
  excepción y no cierra la sesión. Un UoW por módulo.
- El router construye el UoW con una dependencia; el servicio lo abre con `async with`.
- RN-02, RN-13 y RN-20 cada una en un solo bloque.

## Impact
- Capabilities: `persistencia`.
- Archivos: `app/core/repository.py`, `app/core/unit_of_work.py`, `app/modules/*/repository.py`,
  `app/modules/*/unit_of_work.py`, `app/modules/*/service.py`.
