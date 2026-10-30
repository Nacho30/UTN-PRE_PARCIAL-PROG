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

## Ejercicio 5 · Autorización

- Aplicación incremental del change existente `ej5-autorizacion`, con diseño agregado a partir de las instrucciones del CLI, sin cambiar el esquema.
- Safety net tras la corrección previa: 3/3 pruebas existentes.
- RED dependencias/grupos: 11 fallos y 6 casos ya satisfechos (CRUD abierto, roles sin vigencia y cookie anterior aceptada).
- GREEN inicial: 20/20 incluyendo baseline; triangulación de roles revocados/vencidos/futuros y límites iat ±1 microsegundo.
- RED administración: 17 fallos / 22 aprobados (endpoints ausentes y login incluyendo un rol vencido); GREEN 42/42 con baseline.
- RED permisos/propiedad: 14 fallos / 42 aprobados; GREEN 59/59 con baseline.
- Revisión independiente: mecánico asignado con rol revocado o vencido devolvía 409 al llegar al stock, en vez de 403. Dos casos RED y corrección del permiso antes del estado/stock.
- Registro: prueba RED del evento faltante; evento agregado en el mismo bloque que usuario, asignación y ficha.
- Resultado final tras formato: `python -m pytest test_auth.py test_autorizacion.py -q --tb=short`: **72 passed** (69 E5 y 3 baseline). PostgreSQL 18 real y Python 3.13; no se simulan consultas ni commits.
- Las pruebas E5 reutilizan savepoints y ejecutan el seed **dentro de la transacción externa**, sólo si la configuración señala la base desechable `parcial_*` en puerto 55432. El rollback externo restaura los datos. Se reinicia el semáforo únicamente en el fixture para aislar los distintos bucles de pytest al ejecutar los hashes concurrentes del seed.
- Cobertura: todas las causas de 401; 403 con roles vigentes desde la base; historial/reasignación; expiración con zona; autoprotección; cambio obligatorio y cookie vieja/nueva sin espera; bcrypt sin transacción abierta; eventos y paginación; propietarios sin rol CLIENTE; permiso antes de estado; actor real de órdenes/movimientos.
- `test/02_autorizacion.http` contiene la reproducción manual C-06 a C-09. No se afirma ejecución manual de REST Client; la evidencia ejecutada es pytest HTTP contra PostgreSQL.
- No hay migraciones nuevas. El esquema de la base aislada fue creado con Alembic (0001 y 0002). No se valida producción ni concurrencia distribuida; el TP excluye el capítulo de concurrencia.

### TDD Cycle Evidence · E5

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1–1.5 identidad, vigencia, permisos y contraseña pendiente | `test_autorizacion.py` | Integración HTTP + PostgreSQL | 3/3 | 11 fallos iniciales | 20/20 | cookie, inactivo, roles revocados/vencidos/futuros, iat -1/0/+1 us | Formato y roles reutilizados; 72/72 |
| 2.1–2.2 grupos abierto/protegido | `test_autorizacion.py` | Integración HTTP + PostgreSQL | 20/20 | CRUD devolvía 200 sin sesión | 20/20 | auth/health accesibles; nuevas rutas 401/403 | 72/72 |
| 3.1–3.4 personal e historial de roles | `test_autorizacion.py` | Integración HTTP + PostgreSQL | 20/20 | rutas 404; 17 fallos de bloque | 42/42 | válido/duplicado, vencido/futuro/sin zona, revocación conserva fila, propio ADMIN | 72/72 |
| 3.5 cambio de contraseña | `test_autorizacion.py` | Integración HTTP + PostgreSQL | 20/20 | endpoint 404 | 42/42 | actual incorrecta/72 bytes, cookie antigua/nueva, sin conexión durante bcrypt | 72/72 |
| 3.6 eventos y permisos de propiedad | `test_autorizacion.py` | Integración HTTP + PostgreSQL | 42/42 | eventos 404; matriz 14 fallos; alta sin evento | 72/72 | paginación; propietario/ajeno; sin ficha; roles actuales de mecánico; actores | 72/72 |


Cierre E5: tras extraer el filtro de vigencia común y agregar la comprobación de actores
reales de movimientos y precios, la ejecución final dio **73 passed** (70 E5 + 3 baseline,
19.62 s). `openspec validate ej5-autorizacion --strict` pasó con 13/13 tareas; se archivó con
`openspec archive ej5-autorizacion --yes`, creando `openspec/specs/autorizacion/spec.md`
con sus cinco requisitos. `openspec validate autorizacion --type spec --strict` y
`git diff --check` también pasaron. El archivo está en
`openspec/changes/archive/2026-10-30-ej5-autorizacion/`.
