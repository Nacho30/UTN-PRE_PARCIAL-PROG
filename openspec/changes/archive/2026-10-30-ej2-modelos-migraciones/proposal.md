# Ejercicio 2 · Modelos, relaciones y migraciones

## Why
El modelo de dominio (Figura 1) tiene asociación, composición, uno a uno opcional y una tabla
de catálogo. La base tiene que garantizar lo que puede garantizar (RN-01, RN-03, RN-19) y el
esquema tiene que ser reproducible y versionado.

## What Changes
- Modelos SQLModel de las 14 tablas con los nombres obligatorios.
- Tres índices únicos parciales con `postgresql_where`: `asignacion_rol (usuario_id, rol)`,
  `vehiculo (patente)` y `repuesto (codigo)`, sólo sobre filas abiertas o vigentes.
- `estado_orden` como catálogo (PK `codigo`); `orden_trabajo.estado` y los estados del
  historial son claves foráneas a él, no un CHECK.
- Navegación en ambos extremos; `Usuario.cliente` es un objeto (`uselist=False`).
- Toda relación con `lazy="raise_on_sql"`: leer una relación no precargada falla en vez de
  disparar una consulta escondida.
- Índice en cada clave foránea.
- Dos migraciones: `0001` autogenerada (todas las tablas) y `0002` escrita a mano (disparador
  de sólo agregado). El esquema se crea sólo con Alembic; no se usa `create_all`.
- El catálogo se crea vacío; sus filas las carga `seed.py`.

## Impact
- Capabilities: `esquema`.
- Archivos: `app/modules/*/models.py`, `app/core/tipos.py`, `migrations/`, `alembic.ini`.
