-- Caso C-14 · UPDATE y DELETE sobre las tres tablas de sólo agregado, y una orden con un
-- estado que no está en el catálogo.
--
-- ANTES:  python seed.py
-- CORRER: psql -h localhost -U taller -d taller -f test/solo_agregado.sql
--
-- Cada sentencia corre sola (autocommit) para que un rechazo no aborte las siguientes.
-- Esperado: las seis primeras, rechazadas por el disparador; la séptima, por la clave foránea.

\set ON_ERROR_STOP off
\echo '--- 1/7 UPDATE historial_estado_orden'
UPDATE historial_estado_orden SET hasta_estado = 'CANCELADA' WHERE id = 1;
-- ERROR:  historial_estado_orden es de sólo agregado: no se permite UPDATE

\echo '--- 2/7 DELETE historial_estado_orden'
DELETE FROM historial_estado_orden WHERE id = 1;
-- ERROR:  historial_estado_orden es de sólo agregado: no se permite DELETE

\echo '--- 3/7 UPDATE movimiento_stock'
UPDATE movimiento_stock SET cantidad = 99 WHERE id = 1;
-- ERROR:  movimiento_stock es de sólo agregado: no se permite UPDATE

\echo '--- 4/7 DELETE movimiento_stock'
DELETE FROM movimiento_stock WHERE id = 1;
-- ERROR:  movimiento_stock es de sólo agregado: no se permite DELETE

\echo '--- 5/7 UPDATE historial_precio_repuesto'
UPDATE historial_precio_repuesto SET precio_nuevo = 1 WHERE id = 1;
-- ERROR:  historial_precio_repuesto es de sólo agregado: no se permite UPDATE

\echo '--- 6/7 DELETE historial_precio_repuesto'
DELETE FROM historial_precio_repuesto WHERE id = 1;
-- ERROR:  historial_precio_repuesto es de sólo agregado: no se permite DELETE

\echo '--- 7/7 orden con un estado que no está en el catálogo'
INSERT INTO orden_trabajo (vehiculo_id, estado, falla, total) VALUES (1, 'INVENTADO', 'Prueba', 0);
-- ERROR:  insert or update on table "orden_trabajo" violates foreign key constraint
--         "fk_orden_trabajo_estado_estado_orden"

\echo '--- control: agregar SÍ se puede (y se revierte para no ensuciar)'
BEGIN;
INSERT INTO movimiento_stock (repuesto_id, usuario_id, cantidad, motivo) VALUES (1, 1, 1, 'Prueba de agregado');
-- INSERT 0 1
ROLLBACK;

\echo '--- las filas siguen como estaban'
SELECT id, desde_estado, hasta_estado FROM historial_estado_orden ORDER BY id;
SELECT id, repuesto_id, cantidad, motivo FROM movimiento_stock ORDER BY id;
SELECT id, repuesto_id, precio_anterior, precio_nuevo FROM historial_precio_repuesto ORDER BY id;
