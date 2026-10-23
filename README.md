# Taller mecánico · Ejercicios 1 y 2

TP de **Programación III** (UTN · Tecnicatura Universitaria en Programación), unidades 1 a 6.
Esta entrega cubre:

- **Ejercicio 1 · Proyecto, configuración y ciclo de vida**: estructura obligatoria, `Settings`
  sin secretos por defecto, motor y fábrica de sesiones creados en el lifespan, `get_session`,
  `GET /health/live` y `GET /health/ready`.
- **Ejercicio 2 · Modelos, relaciones y migraciones**: los modelos del dominio con todas sus
  restricciones, los tres índices únicos parciales, el catálogo `estado_orden` con clave
  foránea, y dos migraciones de Alembic (una autogenerada y otra escrita a mano con el
  disparador de sólo agregado).

Los archivos de los ejercicios siguientes ya están en la estructura, con un docstring que
indica en qué ejercicio se completan.

Desarrollado con **SDD (Spec-Driven Development)** y OpenSpec: cada ejercicio es un *change*
en [`openspec/changes/`](openspec/changes) con su propuesta, sus tareas y el delta de specs.

## Puesta en marcha desde cero

Requisitos: Python 3.12+ y PostgreSQL 16.

### 1. Base de datos

```sql
-- como superusuario de PostgreSQL
CREATE USER taller WITH PASSWORD 'una-contraseña-local';
CREATE DATABASE taller OWNER taller;
```

### 2. Entorno virtual y dependencias

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 3. Archivo `.env`

```bash
cp env.example .env        # en Windows: copy env.example .env
```

Completar `POSTGRES_PASSWORD` con la del paso 1 y generar la clave de firma de los tokens:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

y pegarla en `JWT_SECRET`. **Ninguna de las dos tiene valor por defecto**: si faltan, la
aplicación no arranca. El `.env` no se sube al repositorio.

### 4. Esquema y datos iniciales

```bash
alembic upgrade head      # 0001: todas las tablas · 0002: disparador de sólo agregado
python seed.py            # carga el catálogo de estados y los datos iniciales
```

Las migraciones crean el catálogo `estado_orden` **vacío**: sus cuatro filas las carga `seed.py`.

Para comprobar que las migraciones van y vuelven, y que coinciden con los modelos:

```bash
alembic downgrade base && alembic upgrade head
alembic check             # "No new upgrade operations detected."
```

### 5. Servidor

```bash
fastapi dev main.py       # o: uvicorn main:app --reload
```

- <http://localhost:8000/health/live> → 200 (no toca la base)
- <http://localhost:8000/health/ready> → 200 con la base arriba, 503 si la base no contesta

### 6. Disparador de sólo agregado

```bash
psql -h localhost -U taller -d taller -f test/solo_agregado.sql
```

Esperado: seis rechazos del disparador (UPDATE y DELETE sobre `historial_estado_orden`,
`movimiento_stock` e `historial_precio_repuesto`) y uno de la clave foránea (una orden con un
estado que no está en el catálogo).

## Estructura

```
main.py                         app, lifespan y los dos grupos de rutas
seed.py                         estado inicial conocido
app/
  modelos.py                    registra todos los modelos (lo usan main, seed y Alembic)
  core/
    config.py                   Settings (pydantic-settings), database_url con @computed_field
    database.py                 crear_engine, crear_session_factory, get_session
    security.py                 bcrypt en to_thread + semáforo (hash ficticio del lifespan)
    tipos.py                    naming_convention y columnas timestamptz / NUMERIC
    dependencies.py             (ejercicios 4 y 5)
    repository.py               (ejercicio 6)
    paginacion.py               (ejercicio 3)
    unit_of_work.py             (ejercicio 6)
  modules/
    health/router.py            /health/live y /health/ready
    usuarios/models.py          Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
    clientes/models.py          Cliente, Vehiculo
    repuestos/models.py         Repuesto, MovimientoStock, HistorialPrecio
    ordenes/models.py           EstadoOrden, OrdenTrabajo, ItemOrden, HistorialEstadoOrden
    <módulo>/{schemas,repository,unit_of_work,service,router}.py   (ejercicios 3 a 6)
migrations/                     Alembic, plantilla asincrónica
  versions/0001_esquema_inicial.py   autogenerada, revisada
  versions/0002_solo_agregado.py     escrita a mano
test/solo_agregado.sql          prueba del disparador
openspec/                       specs SDD de los ejercicios 1 y 2
```

## Decisiones del modelo

- **Patente y código únicos sólo entre los vigentes**: índices únicos parciales con
  `WHERE borrado_en IS NULL`, porque vehículos y repuestos tienen borrado lógico.
- **Una asignación abierta por rol**: índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`.
- **Catálogo en lugar de CHECK**: `orden_trabajo.estado` y los estados del historial son claves
  foráneas a `estado_orden.codigo`.
- **Uno a uno opcional**: `cliente.usuario_id` UNIQUE y nulo; `Usuario.cliente` devuelve un objeto.
- **Índice en cada clave foránea** (PostgreSQL no los crea solo).
- **Sin carga perezosa**: todas las relaciones con `lazy="raise_on_sql"`.
- **Fechas `timestamptz` y dinero `NUMERIC`** (`Decimal` en Python, nunca `float`).
