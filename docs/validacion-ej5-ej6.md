# Validación local de los ejercicios 5 y 6

## Corrección previa autorizada: login y pruebas repetibles

- Entorno: Python 3.13, PostgreSQL 18 local aislado; esquema creado con `alembic upgrade head` (0001 y 0002).
- Baseline original: `python -m pytest -q --tb=short` dio **1 passed, 1 failed**. El login fallaba antes de ejecutar el servicio: la dependencia lambda referenciaba `request` fuera de su ámbito (`NameError`).
- Corrección: usar el `Request` que FastAPI ya inyecta en el handler para obtener `app.state.session_factory`.
- Aislamiento: la fixture abre una transacción externa y entrega sesiones con `join_transaction_mode="create_savepoint"`; al salir revierte la transacción externa. No vacía tablas ni elimina bases de datos. Requiere PostgreSQL con migraciones aplicadas y configuración local en el entorno o `.env` ignorado.
- Regresión: recorrido registro/login/yo/logout y contraseña incorrecta (401 sin cookie).
- RED con ambas pruebas de login: **2 failed, 1 passed**, ambas por el mismo `NameError`.
- GREEN: **3 passed** en dos ejecuciones consecutivas (1.61 s y 1.52 s).
- Comprobación posterior: permanecieron sólo las filas anteriores al fixture (1 usuario y 1 cliente del baseline original); los intentos de las pruebas no persistieron (0).
- Advertencias previas no modificadas: `datetime.utcnow()` en el repositorio de intentos; alcance de loop de fixture sin configurar en pytest-asyncio.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Corregir dependencia del login | `test_auth.py` | Integración HTTP + PostgreSQL | 1/2, fallo previo autorizado | 2 fallos por NameError | 3/3 | Login correcto + contraseña incorrecta | Cambio mínimo, repetición 3/3 |

No se hizo push ni se creó un PR.
