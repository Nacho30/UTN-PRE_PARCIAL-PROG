# Tareas · Ejercicio 7

> Las tareas 1, 2, 3, 5 y 6 quedaron hechas en el ejercicio 2 (migración `0002_solo_agregado`
> y `test/solo_agregado.sql`). El `AccesoUnitOfWork` existía desde el ejercicio 6, y la ventana
> de 60 s y el `Retry-After` los corrigió el commit `7dcb823` (ejercicio 4). Acá se dejó el
> chequeo del login en una sola consulta y se agregaron las pruebas.

## 1. Sólo agregado (RN-15)
- [x] 1.1 Función `rechazar_modificacion()` en PL/pgSQL con `RAISE EXCEPTION` y SQLSTATE propio
- [x] 1.2 Disparadores en `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto`
- [x] 1.3 `downgrade` que quita disparadores y función
- [x] 1.4 `test/solo_agregado.sql`: 3 UPDATE + 3 DELETE rechazados y una orden con estado inexistente
- [x] 1.5 Pruebas en `test_integridad.py`: los seis rechazos, el INSERT permitido, la clave foránea y que la migración instale el disparador en las tres tablas

## 2. Intento de acceso en su propia transacción (RN-08)
- [x] 2.1 `AccesoUnitOfWork` con sesión propia, confirmada siempre; comentario con la razón y el costo
- [x] 2.2 Comentario en el login que declara que es la única escritura fuera de la transacción de la petición
- [x] 2.3 Ventana de 60 s y posterior al último éxito (`get_fallos_recientes`, commit `7dcb823`); el login la usa en **una** consulta en vez de contar y después buscar el quinto fallo
- [x] 2.4 `ErrorDemasiadosIntentos` con `retry_after` y el manejador global que lo pone en `Retry-After` (commit `7dcb823`)
- [x] 2.5 `Retry-After` calculado desde el fallo más viejo de la ventana
- [x] 2.6 Pruebas en `test_integridad.py`: seis fallos (el sexto 429 sin hash), ventana, ventana mezclada, éxito que reinicia, otra IP, `Retry-After` y que el 429 cueste una sola consulta

## 3. Evidencia
- [x] 3.1 Salida de `psql` con los seis rechazos y el de la clave foránea: `docs/evidencias/C-14_psql_solo_agregado.txt`

> La captura de pantalla (PNG) de esa salida para la entrega queda en los pendientes del
> roadmap: se saca en la máquina de quien entrega.
