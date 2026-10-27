# Tareas · Ejercicio 7

> Las tareas 1, 2, 3, 5 y 6 ya quedaron hechas en el ejercicio 2 (migración `0002_solo_agregado`
> y `test/solo_agregado.sql`). Falta el intento de acceso en su propia transacción y la captura.

- [x] 1. Función `rechazar_modificacion()` en PL/pgSQL con `RAISE EXCEPTION` y SQLSTATE propio
- [x] 2. Disparadores `trg_solo_agregado` en `historial_estado_orden`, `movimiento_stock` y `historial_precio_repuesto`
- [x] 3. `downgrade` que quita disparadores y función
- [ ] 4. `AccesoUnitOfWork` con sesión propia, documentado en un comentario con su costo
- [x] 5. `test/solo_agregado.sql`: 3 UPDATE + 3 DELETE rechazados y una orden con estado inexistente
- [x] 6. Probar el SQL contra PostgreSQL 16
- [ ] 7. Captura de `psql` con los seis rechazos y el de la clave foránea (evidencia de la entrega)
