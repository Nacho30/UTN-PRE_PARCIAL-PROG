# Ejercicio 1 · Proyecto, configuración y ciclo de vida

## Why
Sin una base de proyecto ordenada, el resto de los ejercicios no tiene dónde apoyarse. Los
recursos (motor y fábrica de sesiones) tienen que nacer dentro del bucle de eventos, y los
secretos no pueden tener valores por defecto (EA-08, sección 1.9; sección 5.12).

## What Changes
- Estructura obligatoria por módulos (`app/core`, `app/modules/<módulo>`, `migrations/`, `test/`).
- `Settings` con pydantic-settings; la URL de la base es un `@computed_field` armado con
  `POSTGRES_*` y driver `postgresql+asyncpg`.
- `JWT_SECRET` y `POSTGRES_PASSWORD` sin valor por defecto: si faltan, la app no arranca.
- Lifespan: crea el motor (pool declarado en la configuración) y la fábrica de sesiones,
  los guarda en `app.state`, calcula una vez el hash ficticio del login y al apagar hace
  `dispose()`.
- `get_session` toma la fábrica de `app.state`, entrega una sesión por petición
  (`expire_on_commit=False`) y la cierra.
- `GET /health/live` (no toca la base) y `GET /health/ready` (`SELECT 1`, 503 si falla).

## Impact
- Capabilities: `plataforma`.
- Archivos: `main.py`, `app/core/config.py`, `app/core/database.py`, `app/modules/health/router.py`,
  `env.example`, `requirements.txt`.
