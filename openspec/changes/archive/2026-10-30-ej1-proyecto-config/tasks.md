# Tareas · Ejercicio 1

## 1. Estructura y configuración
- [x] 1.1 Crear la estructura obligatoria de carpetas y módulos
- [x] 1.2 `Settings` con pydantic-settings leyendo entorno y `.env`
- [x] 1.3 `database_url` como `@computed_field` con `URL.create` (escapa caracteres especiales)
- [x] 1.4 `POSTGRES_PASSWORD` y `JWT_SECRET` obligatorios, sin default
- [x] 1.5 `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` y `SQL_ECHO` en la configuración
- [x] 1.6 `env.example` con todas las variables y ningún secreto

## 2. Ciclo de vida
- [x] 2.1 `crear_engine` y `crear_session_factory` en `app/core/database.py`
- [x] 2.2 Lifespan que crea motor y fábrica y los guarda en `app.state`
- [x] 2.3 Hash ficticio calculado una vez en el lifespan
- [x] 2.4 `dispose()` del motor al apagar
- [x] 2.5 `get_session` desde `app.state`, con `expire_on_commit=False`, cerrada al terminar

## 3. Salud
- [x] 3.1 `GET /health/live` sin base
- [x] 3.2 `GET /health/ready` con `SELECT 1` y 503 si la base no contesta
