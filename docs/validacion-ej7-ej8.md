# Validación local de los ejercicios 7 y 8

- Entorno: Python 3.13, PostgreSQL 16 local y desechable (`parcial_taller`, puerto 55432),
  esquema creado con `alembic upgrade head` (0001 y 0002) y datos con `python seed.py`.
- Base: `main` en `4c3a50b` (incluye la corrección del ejercicio 4 de `7dcb823`).
- Resultado final: `python -m pytest -q` → **156 passed, 3 failed**. Las 3 fallas
  (`test_auth.py::test_endpoints_registro_atomico_y_72_bytes`,
  `test_endpoints_login_rate_limit_yo_y_logout` y `test_triangulacion_seguridad_y_capas`)
  ya fallan igual en `4c3a50b` sin ningún cambio de E7/E8, con
  `sniffio.AsyncLibraryNotFoundError`: son pruebas sincrónicas que reemplazan
  `anyio.to_thread.run_sync`. Quedan fuera de este alcance.
- `test_integridad.py` (17) y `test_lecturas.py` (15): todas pasan.
- Ciclo de migraciones: `alembic upgrade head` → `alembic downgrade base` →
  `alembic upgrade head` sin errores; `alembic check` → «No new upgrade operations detected».
- `openspec validate ej7-integridad --strict` y `openspec validate ej8-lecturas-asincronia --strict`
  pasaron antes de archivar.

## Ejercicio 7 · Integridad

El disparador (migración 0002) y `test/solo_agregado.sql` venían del ejercicio 2, y el
`AccesoUnitOfWork` del ejercicio 6. Los dos defectos del límite de intentos que anotó
`docs/validacion-ej5-ej6.md` (ventana de 60 s ignorada y `Retry-After` perdido) los corrigió
el commit `7dcb823` del ejercicio 4. Sobre esa corrección, el login quedó haciendo **una**
consulta para decidir el 429 (antes contaba y después buscaba el quinto fallo: dos).

### TDD · E7

| Prueba | Resultado |
|---|---|
| Seis fallos: el sexto 429 con `Retry-After`, sin verificar la contraseña | ✅ |
| Fallos fuera de la ventana no cuentan | ✅ |
| Ventana mezclada (3 viejos + 4 recientes): el 5.º reciente da 429 | ✅ |
| `Retry-After` desde el fallo más viejo de la ventana (≈10 s) | ✅ |
| El repositorio trae los fallos en una consulta | ✅ |
| El login bloqueado (429) hace un solo `SELECT` | ✅ (RED: 2 antes del cambio) |
| Éxito reinicia la cuenta; otra IP no comparte el límite | ✅ |
| 3 UPDATE + 3 DELETE rechazados por el disparador; INSERT permitido; estado fuera del catálogo rechazado por la FK; disparador instalado en las tres tablas | ✅ |

C-14 en `psql`: salida completa en `docs/evidencias/C-14_psql_solo_agregado.txt` (seis
`ERROR: ... es de sólo agregado` y el de `fk_orden_trabajo_estado_estado_orden`; las filas
quedan como estaban).

## Ejercicio 8 · Lecturas y asincronía

### TDD · E8

| Prueba | RED (antes) | GREEN |
|---|---|---|
| Detalle con 2 y 4 ítems: misma cantidad de `SELECT`, y 4 del detalle | 6 del detalle (vehículo y cliente en consultas aparte) | ✅ 4 |
| Detalle trae vehículo y cliente en un JOIN | sin JOIN | ✅ |
| Alta de orden con 2 y 4 ítems: misma cantidad de `SELECT` | un `get_by_id` por ítem | ✅ |
| Terminar con 1 y 3 ítems: mismas lecturas | un `get_by_id` por ítem | ✅ |
| Listado de órdenes: mismas consultas con `size=1` y `size=5` | ya pasaba | ✅ |
| Todas las relaciones `raise_on_sql`; todos los handlers `async def` | ya pasaba | ✅ |
| Aviso: se agenda al terminar, con datos sueltos | módulo inexistente | ✅ |
| Aviso: no se agenda con 409 (sin stock / estado), 403 ni commit fallido | módulo inexistente | ✅ |
| Aviso: arranca con la respuesta ya enviada (`http.response.start` y `body`) | módulo inexistente | ✅ |
| Aviso: `await asyncio.sleep(0.5)` y mensaje en `taller.avisos` | módulo inexistente | ✅ |

### Evidencias con el servidor real

- **C-15** (`docs/evidencias/C-15_consultas_detalle.txt`): `SQL_ECHO=true`, `GET /ordenes/3`
  (2 ítems) y `GET /ordenes/4` (4 ítems): **6 SELECT en las dos**. Dos son de la
  autenticación (usuario y roles vigentes, RN-04) y cuatro del detalle. Sólo cambian los
  parámetros del `IN` de repuestos.
- **C-11 / C-12** (`docs/evidencias/C-12_aviso_segundo_plano.txt`): terminar la orden 2 sin
  stock da 409 con `ROLLBACK` y sin aviso; después de reponer, `COMMIT` → `200 OK` → el aviso
  ~500 ms después.
- `SQL_ECHO=true` imprimía cada consulta dos veces (`echo=True` agrega un handler propio y el
  registro de la app ya escribe en la consola). Ahora sube el nivel del logger
  `sqlalchemy.engine` y cada consulta sale una vez.

## Límites

- La captura de pantalla (PNG) de C-14 que pide el formato de entrega no se generó: hay que
  sacarla en la máquina de entrega. La salida textual está en `docs/evidencias/`.
- No se validó concurrencia (capítulo 7, fuera del TP): dos terminaciones simultáneas
  siguen pudiendo producir una actualización perdida; el `UPDATE` condicionado de
  `StockRepository.mover` impide igual el stock negativo.
- El aviso corre en el mismo proceso: si el proceso se reinicia se pierde y no se reintenta
  (aceptado por la consigna; lo resuelve el capítulo 8).
