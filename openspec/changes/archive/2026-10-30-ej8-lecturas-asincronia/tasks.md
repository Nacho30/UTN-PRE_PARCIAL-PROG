# Tareas · Ejercicio 8

## 1. Sin carga perezosa
- [x] 1.1 `lazy="raise_on_sql"` en todas las relaciones (ya estaba desde el ejercicio 2; ahora lo verifica una prueba que recorre todos los mapeos)

## 2. Lecturas sin N+1
- [x] 2.1 `get_detalle` con `joinedload` (vehículo → cliente, en un JOIN) y `selectinload` (ítems → repuesto, historial): cuatro consultas fijas
- [x] 2.2 Alta de orden: repuestos en una sola consulta (`RepuestoRepository.get_vigentes_por_ids`) en lugar de uno por ítem
- [x] 2.3 Terminar orden: usa el repuesto que precargó `get_detalle` en lugar de pedirlo de nuevo por cada ítem
- [x] 2.4 Listados con la precarga que usa la respuesta (cantidad de consultas independiente del tamaño de página)

## 3. Asincronía
- [x] 3.1 Todos los handlers `async def` (prueba que recorre las rutas); bcrypt en `to_thread`
- [x] 3.2 `avisos.avisar_cliente` con `await asyncio.sleep(0.5)` y un mensaje en el registro `taller.avisos`
- [x] 3.3 Agendado con `BackgroundTasks` en el router, después de que el servicio confirmó; recibe valores sueltos, no objetos del ORM
- [x] 3.4 Pruebas: se agenda al terminar; no se agenda con 403, 409 ni con un commit fallido; corre después de enviar la respuesta

## 4. Diagnóstico y evidencia
- [x] 4.1 `SQL_ECHO=true` muestra cada consulta una sola vez (antes `echo=True` + el registro de la app la duplicaban)
- [x] 4.2 Evidencia C-15: `docs/evidencias/C-15_consultas_detalle.txt` (6 SELECT con 2 ítems y 6 con 4)
- [x] 4.3 Evidencia C-12: `docs/evidencias/C-12_aviso_segundo_plano.txt` (COMMIT → 200 → aviso)
