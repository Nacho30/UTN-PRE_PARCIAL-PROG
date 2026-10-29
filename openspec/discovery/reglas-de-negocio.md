# Reglas de negocio

Cada regla tiene un **garante**: la pieza que la hace cumplir. Cuando la base puede
garantizarla, la garantiza la base. La columna «Ej.» es el ejercicio del [roadmap](../roadmap.md)
que la implementa.

| Regla | Enunciado | Garante | Ej. | Estado |
|---|---|---|---|---|
| RN-01 | Correo de usuario y documento de cliente únicos. Patente y código únicos entre los que no están dados de baja | UNIQUE e índices únicos parciales; 409 con mensaje propio | 2 (base) · 3 (409) | ✅ hecho |
| RN-02 | El auto-registro crea usuario, rol CLIENTE y ficha de cliente: las tres filas o ninguna. Si el documento ya es de un cliente, 409 y no se apropia de esa ficha | Un solo Unit of Work | 4 · 6 | ✅ hecho |
| RN-03 | A lo sumo una asignación abierta por rol | Índice único parcial; 409 | 2 (base) · 5 (409) | 🟡 base lista |
| RN-04 | Los permisos se deciden con los roles vigentes en la base, en cada petición. Los del token son informativos | Dependencia que consulta `asignacion_rol` | 5 | ⏳ |
| RN-05 | Un admin no puede revocarse su ADMIN, y nunca quedan cero administradores vigentes | Servicio; 409 | 5 | ⏳ |
| RN-06 | Con el cambio de contraseña pendiente, sólo se usan `/auth` y `/health` | Dos grupos de rutas; 403 | 5 | ⏳ (grupos creados en ej1) |
| RN-07 | Al cambiar la contraseña, las sesiones previas dejan de valer, aunque sean del mismo segundo; la del propio cambio no | `iat` contra `password_cambiada_en` sin truncar; 401 | 4 · 5 | ✅ hecho |
| RN-08 | 5 fallos con el mismo correo e IP en 60 s → 429 sin verificar. Un login correcto reinicia la cuenta | Conteo sobre `intento_acceso`; `Retry-After` | 4 · 7 | ⏳ (tabla e índice listos) |
| RN-09 | El login responde lo mismo, y tarda lo mismo, exista o no el correo | Mismo mensaje; hash ficticio | 4 | ✅ hecho |
| RN-10 | La orden nace PENDIENTE, con al menos un ítem y sin repuestos repetidos. Precio copiado del repuesto; total calculado por el servidor | DTO: precio y total nunca viajan en el cuerpo | 3 | ✅ hecho |
| RN-11 | Transiciones: PENDIENTE→EN_REPARACION (mecánico, queda asignado), EN_REPARACION→TERMINADA (asignado o admin), PENDIENTE→CANCELADA | Servicio; 409 | 3 · 6 | ⏳ |
| RN-12 | Cancelan la recepción, el admin o el dueño del vehículo. El permiso se evalúa antes que el estado | Servicio; 403 antes que 409 | 3 · 5 | ⏳ |
| RN-13 | Terminar descuenta el stock de cada ítem, deja un movimiento por salida y una línea de historial. Si un repuesto no alcanza, no queda ninguna escritura | Un solo Unit of Work; 409 | 6 | ⏳ |
| RN-14 | El stock sólo cambia por movimientos: alta con stock inicial, reposición y terminación. No se edita por PATCH | Punto único de escritura de stock | 3 · 6 | ✅ hecho |
| RN-15 | `historial_estado_orden`, `movimiento_stock` e `historial_precio_repuesto` son de sólo agregado | Disparador instalado por migración | 2 · 7 | ✅ |
| RN-16 | Un vehículo o repuesto dado de baja no aparece ni se usa en órdenes nuevas; sus datos se conservan. Un vehículo con órdenes abiertas no se da de baja | Borrado lógico; `es_final`; 409 | 3 · 6 | ✅ hecho |
| RN-17 | Lo propio sólo pide estar autenticado: el cliente ve sus vehículos y sus órdenes, ninguna otra | `/mis-*` y comprobación de dueño; 403 | 5 | ⏳ |
| RN-18 | Ningún error devuelve texto interno de la base. Ninguna entrada inválida termina en 500 | Traducción del `IntegrityError`; validación en el contrato | 3 | ✅ hecho |
| RN-19 | Los estados son las filas de `estado_orden`; se consulta desde la API y no se edita. Vacío → crear una orden da 409 propio | Clave foránea; repositorio de sólo lectura | 2 (base) · 6 | ✅ hecho |
| RN-20 | Cada cambio de precio deja una línea en `historial_precio_repuesto` en la misma transacción. Un PATCH que no cambia el precio no deja línea | Un solo Unit of Work; CHECK precio_nuevo <> precio_anterior | 2 (CHECK) · 6 | ✅ hecho |

✅ hecho · 🟡 la parte de base está lista, falta la lógica · ⏳ pendiente
