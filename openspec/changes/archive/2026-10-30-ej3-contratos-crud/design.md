# Diseño · Contratos y CRUD

## Contratos de entrada y salida

- `EntradaEstricta(SQLModel)` configura `model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)` para que cualquier campo no declarado (como `rol` en el registro o `stock` en el PATCH de repuestos) sea rechazado con `422` antes de llegar al servicio.
- Tipos acotados en `app/core/tipos.py`:
  - `IdEntero = Annotated[int, Field(ge=1, le=2_147_483_647)]`
  - `IdPath = Annotated[int, Path(ge=1, le=2_147_483_647)]`
  - `texto(max_len, min_len=1)`: rechaza cadenas vacías tras `strip` y el carácter nulo `\x00` (que PostgreSQL rechaza con error de driver).
  - `Dinero = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]`
- Ningún esquema de salida de `usuarios` expone `password_hash`.

## Paginación (`app/core/paginacion.py`)

```
pages = max(1, ceil(total / size))
si page > pages → 422 «La página {page} no existe: hay {pages}»
```

- Con `total == 0`, `pages` vale `1`: `page=1` devuelve `items=[]` y `page >= 2` responde `422`.
- `total` se calcula con `count` aplicando exactamente los mismos filtros que la consulta de `items`.

## Traducción de errores (`app/core/errores.py`)

```
Servicio lanza ErrorDominio (404 / 409 / 422 / 403 / 401)
   o SQLAlchemy lanza IntegrityError al hacer flush/commit
        │
        ▼
Manejadores en FastAPI traducen por tipo o por constraint_name a JSON {"detail": "..."}
```

| Restricción / Índice | Código | Mensaje |
|---|---|---|
| `uq_usuario_email` | 409 | Ya existe un usuario con ese correo |
| `uq_cliente_documento` | 409 | Ya existe un cliente con ese documento |
| `uq_cliente_usuario_id` | 409 | El usuario ya tiene una ficha de cliente |
| `ux_vehiculo_patente_vigente` | 409 | Ya existe un vehículo vigente con esa patente |
| `ux_repuesto_codigo_vigente` | 409 | Ya existe un repuesto vigente con ese código |
| `ux_asignacion_rol_abierta` | 409 | El usuario ya tiene ese rol asignado |
| `uq_item_orden_orden_id_repuesto_id` | 409 | La orden tiene repuestos repetidos |
| `fk_orden_trabajo_estado_estado_orden` | 409 | El catálogo de estados de orden no está cargado |

## Búsqueda segura con `ILIKE`

El filtro `q` de `GET /repuestos` escapa `\`, `%` y `_` antes de envolver con `%...%` y usa `col.ilike(patron, escape="\\")`, garantizando parámetros ligados y evitando comodines inyectados por el usuario.

## UI Mockups

Decision: no (no UI)
