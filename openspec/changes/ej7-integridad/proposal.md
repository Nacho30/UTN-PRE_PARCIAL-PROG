# Ejercicio 7 · Integridad: sólo agregado e intento de acceso

## Why
El historial de estados, los movimientos de stock y los cambios de precio son registros
contables: no se corrigen. Esa garantía tiene que darla la base, venga la escritura de la API,
de `psql` o de otro programa (RN-15, sección 6.9). Y el intento de login fallido tiene que
quedar anotado aunque la petición se revierta (sección 6.8.1).

## What Changes
- Migración `0002_solo_agregado`, escrita a mano: función `rechazar_modificacion()` y un
  disparador `BEFORE UPDATE OR DELETE ... FOR EACH ROW` en las tres tablas. El `downgrade`
  los quita.
- `AccesoUnitOfWork` con sesión y transacción propias para `intento_acceso`, confirmada
  siempre. Comentario en el código con la razón y el costo.
- `test/solo_agregado.sql` con los seis rechazos y el de la clave foránea (C-14).

## Impact
- Capabilities: `integridad`.
- Archivos: `migrations/versions/0002_solo_agregado.py`, `app/modules/usuarios/unit_of_work.py`,
  `test/solo_agregado.sql`.
