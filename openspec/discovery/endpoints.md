# Endpoints de referencia

Toda ruta del grupo **protegido** responde además 401 sin sesión y 403 con el cambio de
contraseña pendiente.

| Grupo | Método | Ruta | Quién | Códigos | Ej. |
|---|---|---|---|---|---|
| Abierto | GET | `/health/live` | Cualquiera | 200 | 1 ✅ |
| Abierto | GET | `/health/ready` | Cualquiera | 200, 503 | 1 ✅ |
| Abierto | POST | `/auth/registro` | Cualquiera | 201, 409, 422 | 4 |
| Abierto | POST | `/auth/login` | Cualquiera | 200, 401, 422, 429 | 4 |
| Abierto | POST | `/auth/logout` | Cualquiera | 200 | 4 |
| Abierto | GET | `/auth/yo` | Autenticado | 200, 401 | 4 |
| Abierto | POST | `/auth/cambiar-password` | Autenticado | 200, 401, 422 | 5 |
| Protegido | POST | `/usuarios` (alta de personal, contraseña provisoria) | ADMIN | 201, 409, 422 | 5 |
| Protegido | GET | `/usuarios/{id}/roles` | ADMIN | 200, 404 | 5 |
| Protegido | POST | `/usuarios/{id}/roles` | ADMIN | 201, 404, 409, 422 | 5 |
| Protegido | DELETE | `/usuarios/{id}/roles/{rol}` | ADMIN | 200, 404, 409 | 5 |
| Protegido | GET | `/eventos` (`page`, `size`) | ADMIN | 200, 422 | 5 |
| Protegido | POST | `/clientes` | RECEPCION, ADMIN | 201, 409, 422 | 3 |
| Protegido | GET | `/clientes/{id}` (con sus vehículos) | RECEPCION, ADMIN | 200, 404 | 3 |
| Protegido | POST | `/clientes/{id}/vehiculos` | RECEPCION, ADMIN | 201, 404, 409, 422 | 3 |
| Protegido | DELETE | `/vehiculos/{id}` | RECEPCION, ADMIN | 204, 404, 409 | 3 |
| Protegido | GET | `/mis-vehiculos` | Autenticado | 200 | 5 |
| Protegido | GET | `/repuestos` (`q`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 | 3 |
| Protegido | GET | `/repuestos/{id}` | ADMIN, RECEPCION, MECANICO | 200, 404 | 3 |
| Protegido | POST | `/repuestos` (con `stock_inicial`) | ADMIN | 201, 409, 422 | 3 · 6 |
| Protegido | PATCH | `/repuestos/{id}` (descripción y precio) | ADMIN | 200, 404, 422 | 3 · 6 |
| Protegido | DELETE | `/repuestos/{id}` | ADMIN | 204, 404 | 3 |
| Protegido | POST | `/repuestos/{id}/reponer` | ADMIN | 200, 404, 422 | 6 |
| Protegido | GET | `/repuestos/{id}/movimientos` | ADMIN | 200, 404 | 3 |
| Protegido | GET | `/repuestos/{id}/precios` | ADMIN | 200, 404 | 3 |
| Protegido | POST | `/ordenes` | RECEPCION, ADMIN | 201, 409, 422 | 3 · 6 |
| Protegido | GET | `/ordenes` (`estado`, `page`, `size`) | ADMIN, RECEPCION, MECANICO | 200, 422 | 3 |
| Protegido | GET | `/ordenes/{id}` | El personal, o el dueño del vehículo | 200, 403, 404 | 3 · 8 |
| Protegido | POST | `/ordenes/{id}/iniciar` | MECANICO | 200, 404, 409 | 3 |
| Protegido | POST | `/ordenes/{id}/terminar` | El mecánico asignado, o ADMIN | 200, 403, 404, 409 | 6 · 8 |
| Protegido | POST | `/ordenes/{id}/cancelar` | RECEPCION, ADMIN o el dueño | 200, 403, 404, 409 | 3 · 5 |
| Protegido | GET | `/estados-orden` (por posición) | Autenticado | 200 | 3 |
| Protegido | GET | `/mis-ordenes` (`page`, `size`) | Autenticado | 200, 422 | 5 |

> **La ruta de cancelar no lleva `requiere_rol`.** El dueño de un vehículo puede cancelar su
> orden y no tiene un rol de personal. La decisión la toma el servicio: primero quién es (403),
> después si el estado lo permite (409).

## Contratos de ejemplo (de la consigna)

`POST /ordenes` — viajan el vehículo y los ítems; **no** viajan precio, total, estado ni fecha:

```json
{ "vehiculo_id": 2, "falla": "Ruido al frenar",
  "items": [ { "repuesto_id": 2, "cantidad": 1 }, { "repuesto_id": 4, "cantidad": 3 } ] }
```

Respuesta: `id`, `estado`, `patente`, `total`, `creada_en`, `mecanico_id`, `falla`, `cliente`,
`items[]` (con `codigo`, `descripcion`, `precio_unitario`, `subtotal`) e `historial[]`.

`POST /auth/login` — el token va en `Set-Cookie`, no en el cuerpo:

```json
{ "mensaje": "Sesión iniciada", "debe_cambiar_password": false, "expira_en_segundos": 1800 }
```

Listados — envoltorio de la sección 2.9 (`page=3` con 4 ítems y `size=2` → 422 «La página 3 no
existe: hay 2»):

```json
{ "items": [ ... ], "total": 4, "page": 1, "size": 2, "pages": 2 }
```
