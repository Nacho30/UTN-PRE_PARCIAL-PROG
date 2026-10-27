# Stack

| Componente | Versión mínima | Uso |
|---|---|---|
| Python | 3.12 | Lenguaje |
| FastAPI | 0.111 | Framework web; todos los handlers con `async def` |
| SQLModel | 0.0.24 | Modelos de tabla |
| SQLAlchemy | 2.0, asincrónico | Motor, sesión y carga anticipada |
| asyncpg | 0.30 | Driver asincrónico de PostgreSQL (se acepta psycopg 3 async) |
| PostgreSQL | 16 | Base de datos |
| Alembic | 1.13, plantilla asincrónica | Migraciones |
| pydantic-settings | 2.0 | Configuración leída del entorno |
| bcrypt | 4.0 | Hash de contraseñas |
| PyJWT | 2.8 | Token firmado |
| uvicorn | el de `fastapi[standard]` | Servidor ASGI |

Herramientas de trabajo: **OpenSpec** (SDD), **REST Client** de VS Code (casos `.http`), `psql`
(caso C-14), `ruff` (lint, opcional).

## Configuración

Clase `Settings` en `app/core/config.py`, leída del entorno o de un `.env` que **no se versiona**.
`env.example` lista todas las variables sin ningún secreto.

| Variable | Default | Notas |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_DB` / `POSTGRES_HOST` / `POSTGRES_PORT` | taller / taller / localhost / 5432 | |
| `POSTGRES_PASSWORD` | **ninguno** | Obligatoria: sin ella la app no arranca |
| `POSTGRES_DRIVER` | `postgresql+asyncpg` | O `postgresql+psycopg` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 5 / 10 | Tamaño del pool (sección 4.5) |
| `SQL_ECHO` | false | true muestra las consultas (C-15) |
| `JWT_SECRET` | **ninguno** | Obligatoria, mínimo 32 caracteres |
| `JWT_ALGORITHM` / `JWT_EXPIRA_MINUTOS` | HS256 / 30 | |
| `COOKIE_SECURE` | false | true en producción con HTTPS |
| `BCRYPT_ROUNDS` / `BCRYPT_CONCURRENCIA` | 12 / 4 | El costo se sube con los años |
| `LOGIN_MAX_FALLOS` / `LOGIN_VENTANA_SEGUNDOS` | 5 / 60 | RN-08 |

La URL de la base es un `@computed_field` armado con `URL.create` (escapa caracteres especiales
de la contraseña).
