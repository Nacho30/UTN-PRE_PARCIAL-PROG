# Convenciones

## Estructura obligatoria

```
main.py                       app, lifespan y los dos grupos de rutas
seed.py                       estado inicial conocido
app/core/config.py            Settings
app/core/database.py          crear_engine, crear_session_factory, get_session
app/core/security.py          bcrypt fuera del bucle; emisión y verificación del token
app/core/dependencies.py      usuario actual, roles vigentes, cambio obligatorio, requiere_rol
app/core/repository.py        BaseRepository[T], SoftDeleteRepository[T]
app/core/paginacion.py        envoltorio de listados y cálculo de páginas
app/core/unit_of_work.py      UnitOfWork base
app/modules/<módulo>/         models · schemas · repository · unit_of_work · service · router
migrations/                   Alembic y sus versiones
test/                         .http y solo_agregado.sql
openspec/                     SDD: discovery, foundations, roadmap, changes, specs
```

Archivos de apoyo propios (permitidos): `app/modelos.py` (registra todos los modelos),
`app/core/tipos.py` (naming convention y tipos de columna), `app/core/errores.py` (ej3).

## Nombres

- Tablas y columnas: **exactamente** las de la consigna, en `snake_case` y singular.
- Restricciones: por `naming_convention` → `uq_<tabla>_<cols>`, `ck_<tabla>_<nombre>`,
  `fk_<tabla>_<col>_<tabla_ref>`, `ix_<tabla>_<cols>`, `pk_<tabla>`. Índices únicos parciales:
  `ux_<tabla>_<cosa>` (`ux_vehiculo_patente_vigente`, `ux_repuesto_codigo_vigente`,
  `ux_asignacion_rol_abierta`).
- Código, mensajes y comentarios en castellano. Métodos de repositorio nombrados por lo que
  traen (`get_detalle`, `get_by_email`, `get_vigentes_de_usuario`).
- Dependencias de UoW: `get_<módulo>_uow`. UoW: `<Módulo>UnitOfWork`.

## Tipos

- Fechas: `timestamptz`, siempre con zona (`datetime.now(UTC)`).
- Dinero: `NUMERIC(10,2)` (precios) y `NUMERIC(12,2)` (total); `Decimal` en Python, nunca `float`.
- Ids de ruta y de cuerpo: entero entre 1 y 2 147 483 647 (cabe en un `integer`).
- Textos de entrada: con largo máximo y sin el carácter `\x00`.
- Estados de orden: enum en el código (contrato y transiciones) + catálogo en la base. Tienen
  que coincidir.

## Códigos HTTP

| Código | Cuándo |
|---|---|
| 200 | Lectura o acción correcta |
| 201 | Alta |
| 204 | Baja (lógica) |
| 401 | No sé quién sos: sin cookie, token inválido o vencido, usuario inactivo, token previo al cambio de contraseña |
| 403 | Sé quién sos pero no podés: sin rol, no es tuyo, cambio de contraseña pendiente |
| 404 | No existe el recurso de la **ruta** |
| 409 | Choca con lo guardado: unicidad, estado que no permite la transición, stock insuficiente, referencia del cuerpo inexistente |
| 422 | El cuerpo o los parámetros no cumplen el contrato (incluye página inexistente y vencimiento pasado) |
| 429 | Límite de intentos de login, con `Retry-After` |
| 503 | `/health/ready` con la base caída |

Orden de los controles en un servicio: **existe (404) → quién es (403) → estado (409)**.

## Errores

- Cuerpo: `{"detail": "<mensaje propio en castellano>"}`.
- Un `IntegrityError` se traduce por **nombre de restricción** a un 409 con mensaje propio.
- La unicidad no se consulta antes: se intenta la escritura y se traduce el error.
- Un manejador final responde 500 genérico y manda la traza sólo al registro.

## Listados

`{items, total, page, size, pages}`; `page ≥ 1`, `1 ≤ size ≤ 100` (default 20);
`pages = max(1, ceil(total / size))`; página mayor que `pages` → 422 «La página N no existe: hay M»;
`total` con **los mismos filtros** que la página.

## Git

- Rama `main`. Un commit por ejercicio (o por *change*), con mensaje en castellano.
- Nunca se versiona `.env`.
