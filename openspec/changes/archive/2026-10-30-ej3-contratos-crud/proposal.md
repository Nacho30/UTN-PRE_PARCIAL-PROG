# Ejercicio 3 · Contratos y CRUD

## Why
Los modelos de tabla no son el contrato de la API: si lo fueran, cualquiera podría mandar un
rol al registrarse o tocar el stock por PATCH. Además, ninguna entrada inválida puede terminar
en un 500 (RN-18).

## What Changes
- `schemas.py` por módulo, separado de `models.py`; entradas con `extra="forbid"`.
- Ninguna respuesta incluye `password_hash`.
- Tipos de entrada acotados (`IdEntero`, textos con largo máximo y sin `\x00`, `Decimal` con
  `max_digits`) para que ningún valor llegue a la base y la rompa.
- PATCH parcial con `exclude_unset`; un `null` explícito en un campo obligatorio da 422.
- Códigos: 201 al crear, 204 al dar de baja, 404 si no existe el recurso de la ruta, 409 si
  choca con lo guardado, 422 si el cuerpo o los parámetros no cumplen el contrato.
- Envoltorio `{items, total, page, size, pages}` con `page >= 1`, `1 <= size <= 100`
  (default 20), 422 si la página no existe, `total` con los mismos filtros, y una página vacía
  cuando no hay resultados.
- Búsqueda de repuestos por descripción con parámetros ligados (`ILIKE` con escape).

## Impact
- Capabilities: `contratos`.
- Archivos: `app/modules/*/schemas.py`, `app/core/paginacion.py`, `app/core/tipos.py`, routers.
