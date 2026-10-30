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

## Ejercicio 6 · Repositorios y Unit of Work

- Safety net antes de editar: **73 passed** en 21.96 s, PostgreSQL 18 real y Python 3.13.
- Se conservaron `BaseRepository`, `SoftDeleteRepository`, los repositorios de entidades
  existentes y el catálogo de sólo lectura. Se caracterizaron sus operaciones reales sin
  reescribir comportamiento ya correcto.
- UoW: RED 2 fallos por no revertir un commit fallido; GREEN 4 casos. No cierra la sesión
  de petición. Los routers inyectan los UoW; los servicios no los construyen.
- Stock: RED 4 casos por `StockRepository` ausente; GREEN 8. UPDATE condicionado y
  movimiento comparten transacción. Otro RED de 4 casos detectó que alta, reposición,
  terminación y seed aún evitaban ese punto; se conectaron todos y quedaron 16 casos verdes.
- Registro: RED 4 casos de documento/teléfono y rechazo sin datos reales; GREEN junto al
  baseline. `documento` obligatorio y `telefono` opcional, como `ClienteCrear`. Personal
  hereda sólo las credenciales comunes y conserva su contrato sin datos de cliente.
- Órdenes: RED 4 casos confirmaban dos salidas del mismo UoW por operación. Se eliminó la
  apertura anidada; el repositorio refresca las colecciones cargadas y la respuesta incluye
  el historial recién escrito, también al cancelar y terminar.
- Atomicidad real: stock insuficiente en primer y segundo ítem y fallo final de historial
  conservan stock, movimientos, estado e historial. Fallo de ficha/evento revierte el registro.
  Fallo posterior al flush de precio revierte tanto precio como historial; descripción sola
  no agrega otra línea.
- Acceso: RED 3 casos de propiedad/inyección; GREEN. Prueba adicional con **dos conexiones
  PostgreSQL distintas** demuestra que el intento queda confirmado aunque la petición se
  revierta (rechazo dentro y fuera del bloque de acceso). Sólo se limpia la fila aleatoria de
  esa prueba, con guardia de base desechable; no se elimina ninguna base.
- Catálogo: RED 2 casos por mensaje distinto del spec; ahora devuelve el 409 requerido,
  «El catálogo de estados está vacío: falta correr seed.py», sin escribir órdenes.
- Suite completa antes del formato: **124 passed** (73 previos y 51 E6), 36.70 s.
- Verificación final tras formato: **124 passed**, 32.56 s; cuatro advertencias previas.
- `test/06_transacciones.http` y README actualizados. No se afirma ejecución manual de REST
  Client. No hay migraciones nuevas ni validación de producción o concurrencia distribuida.

### TDD Cycle Evidence · E6

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 BaseRepository | `test_persistencia.py` | PostgreSQL | 73/73 | Existente, sin cambio productivo | CRUD y flush verificados | válido + unicidad/rollback | Conservado |
| 1.2 SoftDeleteRepository | `test_persistencia.py` | PostgreSQL | 73/73 | Existente, sin cambio productivo | 2 casos | IDs distintos, filtro/count/lectura histórica | Conservado |
| 1.3 UnitOfWork | `test_persistencia.py` | Unit | 73/73 | 2 fallos commit sin rollback | 4 casos | éxito/error de cuerpo/2 errores commit | Mínimo try/rollback |
| 2.1 usuarios y acceso | `test_persistencia.py` | Unit + HTTP + 2 conexiones PG | 73/73 | 3 fallos propiedad/inyección | Propiedad e inyección verificadas | acceso normal/rechazado, intento sobrevive rollback | Sin imports dinámicos |
| 2.2 clientes | `test_persistencia.py` | PostgreSQL | 73/73 | Existente, sin cambio productivo | Composición y sesión compartida | clientes + vehículos | Conservado |
| 2.3 repuestos | `test_persistencia.py` | PostgreSQL | 73/73 | 4 fallos StockRepository ausente | Entradas/salidas y rechazos | cero/insuficiente/FK inválida | Punto único |
| 2.4 órdenes | `test_persistencia.py` | HTTP + PostgreSQL | 73/73 | 4 fallos de bloque y 2 de catálogo | 4 operaciones en un bloque | historial actualizado + catálogo readonly | Precarga refrescada |
| 3.1 RN-02 | `test_persistencia.py`, `test_auth.py` | HTTP + PostgreSQL | 73/73 | 4 fallos contrato/ficha | Registro y rollback verificados | teléfono/null; documento repetido; evento falla | UoW inyectado |
| 3.2 RN-13 | `test_persistencia.py` | HTTP + PostgreSQL | 73/73 | Bloque anidado/punto stock | Estado/stock/movimientos/historial atómicos | éxito, 1.º/2.º insuficiente, fallo final | Sin commits anidados |
| 3.3 RN-20 | `test_persistencia.py` | HTTP + PostgreSQL | 73/73 | Existente, sin reescritura | Cambio + historial y rollback | fallo tras flush + descripción sola | Conservado |
| 3.4 RN-14 | `test_persistencia.py` | HTTP + PostgreSQL | 73/73 | 4 operaciones evitaban mover | Alta/reposición/terminación/seed | cantidades positivas/negativas | Stock centralizado |

### Limitaciones previas fuera de este alcance

E4 mantiene dos defectos previos: `contar_fallos_recientes` no aplica `ventana_segundos`,
y el `Retry-After` escrito en `Response` no se copia al JSONResponse del manejador global
de `ErrorDominio`. No se corrigieron ni se declara completo ese comportamiento de E4/E7.
Persisten las advertencias previas de `datetime.utcnow()` y del alcance de loop en pytest.


Cierre E6: `openspec instructions apply` confirmó **11/11 tareas**, `state=all_done`.
`openspec validate ej6-repositorios-uow --strict` pasó y `openspec archive
ej6-repositorios-uow --yes` sincronizó cinco requisitos en `openspec/specs/persistencia/spec.md`
y archivó en `openspec/changes/archive/2026-10-30-ej6-repositorios-uow/`. Se reemplazó el
propósito placeholder que genera el CLI antes de validar estrictamente la especificación
principal. No se cambiaron los pendientes E7/E8.
