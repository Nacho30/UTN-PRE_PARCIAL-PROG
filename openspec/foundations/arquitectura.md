# Arquitectura

## Capas

```
HTTP ─▶ Router ─▶ Service ─▶ Unit of Work ─▶ Repository ─▶ Model ─▶ PostgreSQL
```

| Capa | Archivo | Sabe | No sabe |
|---|---|---|---|
| Router | `modules/<m>/router.py` | Rutas, dependencias de permiso, códigos HTTP. **Construye** el UoW con una dependencia, llama al servicio y traduce errores de dominio a HTTP | Reglas de negocio, SQL |
| Service | `modules/<m>/service.py` | Reglas de negocio. **Recibe** el UoW y lo **abre** con `async with`; lanza errores de dominio | HTTP; nunca construye el UoW |
| Unit of Work | `modules/<m>/unit_of_work.py` | Compone los repositorios del módulo sobre una misma sesión. **Confirma** al salir del bloque, **revierte** con excepción | No cierra la sesión (no la creó) |
| Repository | `modules/<m>/repository.py` | Consultas por entidad; la **precarga** se declara en el método que la usa. `add`/`update` hacen `flush()` | Nunca `commit()` |
| Model | `modules/<m>/models.py` | Tablas, restricciones, relaciones | Contratos de la API |
| Schemas | `modules/<m>/schemas.py` | Contratos de entrada (`extra="forbid"`) y salida | La base |

## Quién crea, abre, confirma y cierra

| Pieza | Crea | Abre | Confirma / revierte | Cierra |
|---|---|---|---|---|
| Motor y fábrica de sesiones | el lifespan (`app.state`) | — | — | el lifespan (`dispose()`) |
| Sesión | `get_session`, una por petición | — | — | `get_session` |
| Unit of Work | la dependencia `get_<m>_uow` del router | el servicio (`async with`) | `UnitOfWork.__aexit__` | nunca |
| Repositorio | el UoW del módulo | — | nunca (sólo `flush`) | — |

**Única excepción:** el UoW de intentos de acceso crea su propia sesión desde la fábrica, la
confirma siempre y la cierra, porque el fallo que se cuenta es el mismo que revierte la
transacción del login (sección 6.8.1, RN-08).

## Jerarquías del núcleo (`app/core`)

| Pieza | Qué ofrece | Ej. |
|---|---|---|
| `BaseRepository[T]` | Recibe sesión y **clase del modelo**; `get_by_id`, `get_all`, `count`, `add`, `update`, `delete` | 6 |
| `SoftDeleteRepository[T]` | Filtra dados de baja; `get_by_id_including_deleted`, `soft_delete` | 6 |
| Repositorio del catálogo | Sólo lectura; **no** hereda de `BaseRepository` | 6 |
| Punto único de stock | `UPDATE ... WHERE stock + n >= 0` + su `movimiento_stock` | 6 |
| `UnitOfWork` | Gestor de contexto asincrónico | 6 |
| `Pagina[T]` | `{items, total, page, size, pages}` | 3 |
| Errores de dominio | 401, 403, 404, 409, 422, 429 sin depender de HTTP en el servicio | 3 |

## Grupos de rutas (`main.py`)

```
abierto   = /health, /auth                      (sin control de cambio de contraseña)
protegido = usuarios, clientes, repuestos, ordenes
            dependencies=[exigir_password_al_dia]  ← montado UNA sola vez
```

FastAPI suma dependencias y no las resta (sección 5.10): si el control estuviera en toda la app,
`/auth/cambiar-password` quedaría bloqueado justo para quien tiene que usarlo (RN-06).

## Dependencias entre módulos

```
health    (ninguna)
usuarios  ─▶ clientes (el registro crea la ficha de cliente)
clientes  ─▶ usuarios (Cliente.usuario)
repuestos ─▶ usuarios (quién movió el stock)
ordenes   ─▶ clientes, repuestos, usuarios
```

## Transacciones de varias escrituras (un solo bloque cada una)

| Operación | Escrituras | Regla |
|---|---|---|
| Auto-registro | usuario + asignacion_rol + cliente + evento | RN-02 |
| Alta de orden | orden_trabajo + item_orden × n + historial | RN-10 |
| Terminar orden | repuesto (stock) × n + movimiento_stock × n + orden_trabajo + historial | RN-13 |
| Cambio de precio | repuesto + historial_precio_repuesto | RN-20 |
| Alta de repuesto con stock | repuesto + movimiento_stock | RN-14 |
