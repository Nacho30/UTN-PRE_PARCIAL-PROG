# Taller mecánico · Órdenes de trabajo, stock y acceso con FastAPI y PostgreSQL

Trabajo Práctico Integrador de **Programación III** (UTN · Tecnicatura Universitaria en Programación), unidades 1 a 6: *Del objeto a la transacción*.

## Alcance implementado (Ejercicios 1 a 5; ejercicio 6 en revisión)

- **Ejercicio 1 · Proyecto, configuración y ciclo de vida (`ej1-proyecto-config`)**:
  - Estructura obligatoria por módulo funcional (`health`, `usuarios`, `clientes`, `repuestos`, `ordenes`).
  - Configuración tipada con `Settings` (`pydantic-settings`) y `database_url` armado con `@computed_field`, sin valores por defecto para secretos (`POSTGRES_PASSWORD` y `JWT_SECRET`).
  - Motor asincrónico (`create_async_engine`), fábrica de sesiones (`expire_on_commit=False`) y hash ficticio de login inicializados dentro del `lifespan` en `app.state` (evitando crear recursos antes del bucle de eventos), con `engine.dispose()` al apagar.
  - Endpoints de salud: `GET /health/live` (200 sin tocar la base) y `GET /health/ready` (`SELECT 1`, 200 o 503 si la base no responde).

- **Ejercicio 2 · Modelos, relaciones y migraciones (`ej2-modelos-migraciones`)**:
  - Modelos SQLModel con las 12 tablas y columnas exactas de la consigna, `timestamptz` con zona horaria y `NUMERIC` (`Decimal`, nunca `float`).
  - Tres índices únicos parciales (`postgresql_where`): `ux_vehiculo_patente_vigente`, `ux_repuesto_codigo_vigente` (`WHERE borrado_en IS NULL`) y `ux_asignacion_rol_abierta` (`WHERE revocada_en IS NULL`).
  - Catálogo `estado_orden` apuntado por clave foránea desde `orden_trabajo` e `historial_estado_orden` (RN-19), relación 1 a 1 opcional `Usuario.cliente` y navegación bidireccional con `lazy="raise_on_sql"`.
  - Esquema gestionado exclusivamente con Alembic (plantilla asincrónica): migración `0001_esquema_inicial.py` (autogenerada y revisada) y `0002_solo_agregado.py` (escrita a mano con el disparador `impedir_modificacion_solo_agregado` sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`, RN-15).
  - Script `seed.py` idempotente (`TRUNCATE ... RESTART IDENTITY CASCADE`) con el catálogo de estados y los datos iniciales de prueba.

- **Ejercicio 3 · Contratos y CRUD (`ej3-contratos-crud`)**:
  - Contratos de entrada y salida (`schemas.py`) separados de los modelos de tabla (`models.py`).
  - Clase base `EntradaEstricta` con `extra="forbid"` y `str_strip_whitespace=True` (impide inyectar campos no declarados como `rol` en el registro o `stock` en el `PATCH` de repuestos).
  - Tipos acotados reutilizables (`IdEntero`, `IdPath`, `texto(max_len)` sin `\x00`, `Dinero`, `PasswordTexto` hasta 72 bytes UTF-8) y normalización de patentes, códigos y correos.
  - Ninguna respuesta de usuario incluye `password_hash`.
  - `PATCH /repuestos/{id}` parcial con `exclude_unset=True`: registra automáticamente una fila en `historial_precio_repuesto` en la misma transacción sólo cuando el precio cambia (RN-20).
  - Paginación genérica `Pagina[T]` (`{items, total, page, size, pages}`) con `page >= 1`, `1 <= size <= 100` (por defecto 20), `pages = max(1, ceil(total / size))` y error `422` (`«La página N no existe: hay M»`) cuando se pide una página fuera de rango.
  - Búsqueda de repuestos por descripción (`GET /repuestos?q=...`) con parámetros ligados e `ILIKE` escapando comodines (`\`, `%`, `_`).
  - Traducción de `IntegrityError` por nombre de restricción/índice único a `409 Conflict` con mensaje propio en castellano (RN-18), y manejador global `500` genérico que nunca expone trazas ni SQL interno al cliente.

---

## Arquitectura en capas y SDD (OpenSpec)

```
HTTP ─▶ Router ─▶ Service ─▶ Unit of Work ─▶ Repository ─▶ Model ─▶ PostgreSQL
```

| Capa | Responsabilidad | Regla clave |
|---|---|---|
| **Router** (`router.py`) | Rutas HTTP, validación de contratos, códigos de estado (200, 201, 204) | Construye el UoW con `Depends` y delega en el servicio |
| **Schemas** (`schemas.py`) | Contratos de entrada (`extra="forbid"`) y salida | Separados de `models.py`; nunca exponen `password_hash` |
| **Service** (`service.py`) | Reglas de negocio y coordinación transaccional | Recibe el UoW y lo abre con `async with`; nunca lo construye ni conoce HTTP |
| **Unit of Work** (`unit_of_work.py`) | Agrupa repositorios sobre la misma `AsyncSession` | Confirma (`commit`) al salir del bloque o revierte (`rollback`) ante excepción; no cierra la sesión |
| **Repository** (`repository.py`) | Consultas por entidad y precarga (`selectinload`) | `add` y `update` hacen `flush()`, nunca `commit()` |
| **Model** (`models.py`) | Tablas, índices parciales, `CHECK`, `FK` y relaciones | `lazy="raise_on_sql"` en todas las relaciones |

### Documentación SDD (`openspec/`)

El proyecto se desarrolla con **Spec-Driven Development (SDD)** y **OpenSpec**:

| Artefacto | Qué contiene |
|---|---|
| [`openspec/discovery/`](openspec/discovery/README.md) | **Qué** construir: contexto, actores, modelo de dominio, reglas RN-01 a RN-20, RNF, endpoints, casos C-01 a C-19 y decisiones de diseño |
| [`openspec/foundations/`](openspec/foundations/README.md) | **Cómo** construir: stack, arquitectura en capas, convenciones, seguridad, definición de terminado y flujo SDD |
| [`openspec/roadmap.md`](openspec/roadmap.md) | **En qué orden**: mapa de los 8 *changes*, grafo de dependencias, hitos y avance de puntaje |
| [`openspec/changes/`](openspec/changes) | Un *change* por ejercicio (`ej1` a `ej8`) con `proposal.md`, `design.md`, `specs/` y `tasks.md` |
| [`AGENTS.md`](AGENTS.md) | Instrucciones y reglas operativas para agentes de IA |

Estado actual de los *changes*:
- ✅ `ej1-proyecto-config` (completado y archivado)
- ✅ `ej2-modelos-migraciones` (completado y archivado)
- ✅ `ej3-contratos-crud` (completado, validado y archivado)
- ✅ `ej4-autenticacion` (archivado; login corregido y probado).
- ✅ `ej5-autorizacion` (autorización y propiedad verificadas; ver validación local).
- ⏳ `ej6-repositorios-uow`, `ej7-integridad`, `ej8-lecturas-asincronia` (pendientes de cierre).

---

## Puesta en marcha desde cero

**Requisitos:** Python 3.12+ y PostgreSQL 16+.

### 1. Crear usuario y base de datos en PostgreSQL

```sql
-- Ejecutar como superusuario de PostgreSQL (ej. postgres)
CREATE USER taller WITH PASSWORD 'una-contraseña-local';
CREATE DATABASE taller OWNER taller;
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Configurar el archivo `.env`

Copiar la plantilla incluida en el repositorio:

```bash
# Linux / macOS
cp env.example .env

# Windows (PowerShell / CMD)
copy env.example .env
```

Generar una clave de firma segura para `JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Editar `.env` completando `POSTGRES_PASSWORD` (la contraseña definida en el paso 1) y `JWT_SECRET` (el valor generado). **Ninguna de las dos variables tiene valor por defecto en el código**: si faltan o quedan vacías, la aplicación rechaza el arranque. El archivo `.env` está ignorado en `.gitignore` y nunca se sube al repositorio.

### 4. Aplicar migraciones con Alembic y cargar datos iniciales

```bash
alembic upgrade head      # Aplica 0001 (tablas, índices, FKs, CHECKs) y 0002 (disparador sólo agregado)
python seed.py            # Vacía las tablas y carga el catálogo estado_orden y los datos iniciales
```

> **Importante:** Las migraciones crean la tabla catálogo `estado_orden` vacía; sus cuatro filas (`PENDIENTE`, `EN_REPARACION`, `TERMINADA`, `CANCELADA`) son datos que carga `seed.py`.

Para verificar ida y vuelta de migraciones y consistencia con los modelos:

```bash
alembic downgrade base && alembic upgrade head
alembic check             # Debe responder: "No new upgrade operations detected."
```

### 5. Levantar el servidor ASGI

```bash
fastapi dev main.py       # o bien: uvicorn main:app --reload
```

Documentación interactiva disponible en:
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

---

## Endpoints disponibles (Ejercicios 1 a 3)

| Grupo | Método | Ruta | Descripción | Códigos HTTP |
|---|---|---|---|---|
| Abierto | `GET` | `/health/live` | Liveness check (no toca la base) | `200` |
| Abierto | `GET` | `/health/ready` | Readiness check (`SELECT 1`) | `200`, `503` |
| Abierto | `POST` | `/auth/registro` | Auto-registro de cliente con contrato estricto (`extra="forbid"`) | `201`, `409`, `422` |
| Protegido | `POST` | `/clientes` | Alta de cliente | `201`, `409`, `422` |
| Protegido | `GET` | `/clientes/{id}` | Detalle de cliente con sus vehículos vigentes | `200`, `404`, `422` |
| Protegido | `POST` | `/clientes/{id}/vehiculos` | Alta de vehículo asociado al cliente | `201`, `404`, `409`, `422` |
| Protegido | `DELETE` | `/vehiculos/{id}` | Baja lógica de vehículo (bloqueada con `409` si tiene órdenes abiertas, RN-16) | `204`, `404`, `409`, `422` |
| Protegido | `GET` | `/repuestos` | Listado paginado (`q`, `page`, `size`) con búsqueda `ILIKE` ligada | `200`, `422` |
| Protegido | `GET` | `/repuestos/{id}` | Detalle de repuesto vigente | `200`, `404`, `422` |
| Protegido | `POST` | `/repuestos` | Alta de repuesto con `stock_inicial` y movimiento `"Stock inicial"` (RN-14) | `201`, `409`, `422` |
| Protegido | `PATCH` | `/repuestos/{id}` | Edición parcial (`descripcion`, `precio`) e historial de precios (RN-20) | `200`, `404`, `422` |
| Protegido | `DELETE` | `/repuestos/{id}` | Baja lógica de repuesto | `204`, `404`, `422` |
| Protegido | `POST` | `/repuestos/{id}/reponer` | Reposición de stock mediante movimiento (RN-14) | `200`, `404`, `422` |
| Protegido | `GET` | `/repuestos/{id}/movimientos` | Historial de movimientos de stock del repuesto | `200`, `404`, `422` |
| Protegido | `GET` | `/repuestos/{id}/precios` | Historial de cambios de precio del repuesto | `200`, `404`, `422` |
| Protegido | `GET` | `/estados-orden` | Catálogo `estado_orden` ordenado por `posicion` (RN-19) | `200` |
| Protegido | `POST` | `/ordenes` | Apertura de orden con ítems, copia de precios y cálculo de total (RN-10) | `201`, `409`, `422` |
| Protegido | `GET` | `/ordenes` | Listado paginado de órdenes filtrable por `estado` (`page`, `size`) | `200`, `422` |
| Protegido | `GET` | `/ordenes/{id}` | Detalle de orden con vehículo, cliente, ítems, subtotales e historial | `200`, `404`, `422` |
| Protegido | `POST` | `/ordenes/{id}/iniciar` | Transición `PENDIENTE → EN_REPARACION` y asignación de mecánico (RN-11) | `200`, `404`, `409`, `422` |
| Protegido | `POST` | `/ordenes/{id}/terminar` | Transición `EN_REPARACION → TERMINADA` y descuento transaccional de stock (RN-13) | `200`, `404`, `409`, `422` |
| Protegido | `POST` | `/ordenes/{id}/cancelar` | Transición `PENDIENTE → CANCELADA` (RN-11, RN-12) | `200`, `404`, `409`, `422` |

---

## Datos iniciales cargados por `seed.py`

| Usuario (`email`) | Contraseña de prueba | Rol inicial | Notas |
|---|---|---|---|
| `admin@example.com` | `Admin1234!` | `ADMIN` | Administrador principal (id `1`) |
| `admin2@example.com` | `Admin1234!` | `ADMIN` | Segundo administrador (id `2`) |
| `recepcion@example.com` | `Recepcion1234!` | `RECEPCION` | Personal de recepción (id `3`) |
| `mecanico@example.com` | `Mecanico1234!` | `MECANICO` | Asignado a la orden 2 (id `4`) |
| `mecanico2@example.com` | `Mecanico1234!` | `MECANICO` | Segundo mecánico (id `5`) |
| `cliente@example.com` | `Cliente1234!` | `CLIENTE` | Vinculado a la cliente Laura (id `6`) |
| `nuevo@example.com` | `Provisoria1234!` | `MECANICO` | `debe_cambiar_password = true` (id `7`) |

Además se cargan:
- **Clientes y vehículos**: Laura (`30111222`, con vehículos `AB123CD` y `AC456EF`) y Jorge (`28999888`, sin usuario, con vehículo `AD789GH`).
- **Repuestos**: `FIL-001` (Filtro de aceite, stock 10, precio `8500.00` con cambio desde `8000.00`), `FRE-010` (Pastillas de freno, stock 4), `BUJ-200` (Bujía, stock 2) y `ACE-530` (Aceite 5W30, stock 20).
- **Órdenes**: Orden 1 (`PENDIENTE`, vehículo de Laura) y Orden 2 (`EN_REPARACION`, vehículo de Jorge, pide 4 bujías cuando hay 2 en stock para probar el rollback de RN-13).

---

## Pruebas y verificación

### 1. Disparador de sólo agregado y clave foránea de catálogo (Caso C-14)

```bash
psql -h localhost -U taller -d taller -f test/solo_agregado.sql
```

Verifica los **6 rechazos del disparador** (`UPDATE` y `DELETE` sobre `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto`) y el **rechazo por clave foránea** al intentar insertar una orden con un estado inexistente en `estado_orden`.

### 2. Casos de prueba HTTP (`test/*.http`)

Con el servidor corriendo y después de ejecutar `python seed.py`, abrir con la extensión **REST Client** de VS Code:
- [`test/03_ordenes.http`](test/03_ordenes.http): casos C-01 (parámetro de ruta no entero → 422), C-10 (alta de orden con precios copiados y rollback ante repuesto inexistente → 201 / 409) y C-17 (catálogo de estados y filtro por estado inválido → 200 / 422).
- [`test/04_repuestos_y_vehiculos.http`](test/04_repuestos_y_vehiculos.http): casos C-16 (inyección en `q`, paginación con filtro, `PATCH` parcial y rechazo de `stock` → 200 / 422), C-18 (cambio de precio con historial vs cambio sólo de descripción) y C-19 (baja lógica de vehículo y reutilización de patente en otro cliente → 204 / 201 / 409).

---

## Estructura del proyecto

```
main.py                                 Aplicación FastAPI, lifespan, grupos de rutas y manejadores de error
seed.py                                 Carga determinista del estado inicial conocido
alembic.ini                             Configuración de Alembic (sin credenciales)
env.example                             Plantilla de variables de entorno (sin secretos)
requirements.txt                        Dependencias con versiones mínimas de la consigna
AGENTS.md                               Instrucciones para agentes de IA (flujo SDD / OpenSpec)
app/
  modelos.py                            Importa todos los modelos para SQLAlchemy y Alembic
  core/
    config.py                           Settings (pydantic-settings) y database_url (@computed_field)
    database.py                         crear_engine, crear_session_factory y get_session
    security.py                         Hash bcrypt en to_thread bajo semáforo
    tipos.py                            naming_convention, EntradaEstricta, IdEntero, IdPath, texto, Dinero
    paginacion.py                       Pagina[T], ParametrosPagina y calcular_paginacion
    errores.py                          Excepciones de dominio y traducción de IntegrityError a 409
    repository.py                       BaseRepository[T] y SoftDeleteRepository[T] (flush sin commit)
    unit_of_work.py                     UnitOfWork asincrónico base (commit / rollback sin cerrar sesión)
    dependencies.py                     Dependencias de autenticación y autorización (ejercicios 4 y 5)
  modules/
    health/router.py                    GET /health/live y GET /health/ready
    usuarios/
      models.py                         Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
      schemas.py                        DTOs de autenticación, usuarios, roles y eventos (sin password_hash)
      repository.py                     Repositorios de usuarios, roles, eventos e intentos
      unit_of_work.py                   UsuariosUnitOfWork
      service.py                        Servicio de registro de clientes
      router.py                         POST /auth/registro
    clientes/
      models.py                         Cliente y Vehiculo (con índice único parcial por patente vigente)
      schemas.py                        ClienteCrear, VehiculoCrear, ClienteOut, ClienteDetalleOut, VehiculoOut
      repository.py                     ClienteRepository y VehiculoRepository (con control de órdenes abiertas)
      unit_of_work.py                   ClientesUnitOfWork
      service.py                        Reglas de negocio de clientes y baja lógica de vehículos (RN-16)
      router.py                         Rutas CRUD de clientes y vehículos
    repuestos/
      models.py                         Repuesto, MovimientoStock e HistorialPrecio
      schemas.py                        RepuestoCrear, RepuestoPatch, ReponerStockIn y esquemas de salida
      repository.py                     RepuestoRepository (ILIKE escapado), MovimientoStock, HistorialPrecio y StockRepository
      unit_of_work.py                   RepuestosUnitOfWork
      service.py                        Alta con stock inicial, PATCH con historial (RN-20), baja y reposición (RN-14)
      router.py                         Rutas CRUD de repuestos, reposición, movimientos y precios
    ordenes/
      models.py                         EstadoOrden, OrdenTrabajo, ItemOrden e HistorialEstadoOrden
      schemas.py                        OrdenCrear, ItemOrdenCrear, OrdenDetalleOut, OrdenResumenOut, EstadoOrdenOut
      repository.py                     EstadoOrdenRepository (sólo lectura), OrdenTrabajoRepository, ItemOrden, Historial
      unit_of_work.py                   OrdenesUnitOfWork
      service.py                        Apertura con copia de precios (RN-10) y transiciones de estado (RN-11, RN-12, RN-13)
      router.py                         Rutas de órdenes y catálogo de estados
migrations/
  env.py                                Entorno asincrónico de Alembic leyendo Settings
  versions/
    0001_esquema_inicial.py             Migración autogenerada y revisada con las 12 tablas
    0002_solo_agregado.py               Migración escrita a mano con el disparador de sólo agregado (RN-15)
test/
  solo_agregado.sql                     Prueba en psql del disparador y la clave foránea del catálogo (C-14)
  03_ordenes.http                       Casos HTTP de órdenes y catálogo (C-01, C-10, C-17)
  04_repuestos_y_vehiculos.http         Casos HTTP de repuestos, vehículos y paginación (C-16, C-18, C-19)
openspec/                               Artefactos SDD (discovery, foundations, roadmap, changes ej1-ej8, specs)
docs/prompts.md                         Registro de prompts utilizados por ejercicio
```


## Ejercicio 5: autorización y revisión local

Todas las rutas de negocio requieren la cookie `access_token` y una contraseña al día.
`/health` y `/auth` quedan fuera de ese control; `/auth/yo` y `/auth/cambiar-password`
requieren identidad válida. Las autorizaciones consultan las asignaciones vigentes en la
base en cada petición; los roles del token son informativos.

- `POST /usuarios` (ADMIN): `{ "email": "personal@example.com", "nombre": "Personal", "password": "Temporal123!", "roles": ["MECANICO"] }`. Se crea con cambio obligatorio.
- `GET/POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` (ADMIN).
  Para asignar: `{ "rol": "MECANICO", "vence_en": "2030-01-01T00:00:00Z" }`; vencimiento opcional, con zona y futuro.
- `POST /auth/cambiar-password`: `{ "password_actual": "Temporal123!", "password_nueva": "Definitiva123!" }`. Devuelve cookie nueva e invalida inmediatamente las anteriores.
- `GET /eventos?page=1&size=20` (ADMIN): historial de seguridad paginado.
- `GET /mis-vehiculos` y `GET /mis-ordenes`: sólo recursos propios, incluso sin el rol CLIENTE.
- El dueño puede consultar y cancelar su orden; se verifica permiso antes del estado.

Pruebas ejecutadas y límites: [validación local](docs/validacion-ej5-ej6.md).
Casos manuales C-06 a C-09: [autorización HTTP](test/02_autorizacion.http).
Instalar herramientas de prueba en el entorno virtual: `python -m pip install pytest pytest-asyncio httpx`.
La suite E5 valida explícitamente una base desechable `parcial_*` en puerto 55432 antes de
usar seed dentro de savepoints: `python -m pytest test_auth.py test_autorizacion.py -q`.

## Ejercicio 6: transacciones y revisión local

Los routers construyen los Unit of Work; los servicios los abren y los repositorios sólo
hacen `flush`. El UoW revierte también si falla el commit y conserva la sesión de la petición.
`AccesoUnitOfWork` crea, confirma y cierra su propia sesión para conservar los intentos
de login aunque se rechace la petición.

El registro exige el documento real y admite teléfono opcional, igual que `ClienteCrear`:

```json
{"email":"cliente.nuevo@example.com","nombre":"Cliente nuevo","password":"Cliente123!","documento":"40555666","telefono":"2615551234"}
```

Sin documento responde 422; con documento existente, 409 sin usuario, rol ni ficha parcial.
El alta de personal conserva su contrato y no exige datos de cliente.

`StockRepository.mover` concentra stock y movimiento mediante UPDATE condicionado. Lo usan
alta, reposición, terminación y seed. Terminar una orden y cambiar un precio conservan todas
sus escrituras en un solo bloque, con rollback completo ante un fallo.

Pruebas: `python -m pytest -q --tb=short` en la base desechable configurada (`parcial_*`,
puerto 55432). Casos manuales: [transacciones HTTP](test/06_transacciones.http).
Evidencia TDD y límites: [validación local](docs/validacion-ej5-ej6.md).
