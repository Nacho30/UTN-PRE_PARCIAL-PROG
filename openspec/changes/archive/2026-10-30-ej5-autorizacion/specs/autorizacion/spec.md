## Purpose

Definir la identidad, los permisos vigentes y la administración de roles y contraseñas del taller, conservando el historial de seguridad.

## ADDED Requirements

### Requirement: 401 contra 403
`get_usuario_actual` SHALL responder 401 si no hay cookie, si el token es inválido o venció, si
el usuario no existe o está inactivo, o si el token es anterior al último cambio de contraseña.
`requiere_rol` SHALL responder 403 cuando el usuario autenticado no tiene ningún rol vigente de
los pedidos.

#### Scenario: Sin rol
- **WHEN** el cliente pide `GET /repuestos`
- **THEN** responde 403

### Requirement: Roles vigentes en la base
Los permisos SHALL decidirse con las filas de `asignacion_rol` vigentes (no revocadas, ya
empezadas y sin vencer) consultadas en cada petición (RN-04).

#### Scenario: Revocar con la sesión abierta
- **WHEN** el ADMIN revoca el rol RECEPCION de una sesión abierta
- **THEN** la petición siguiente de esa sesión, con la misma cookie, responde 403, `/auth/yo` muestra la diferencia entre `roles_vigentes` y `roles_token`, y la fila revocada sigue en la tabla

### Requirement: Vencimiento válido
El vencimiento de una asignación SHALL llegar con zona horaria y en el futuro; si no, 422.

#### Scenario: Vencimiento sin zona
- **WHEN** se asigna un rol con `vence_en = "2030-01-01T00:00:00"`
- **THEN** responde 422

### Requirement: Autoprotección
Un administrador MUST NOT poder revocarse su propio rol ADMIN, y el sistema MUST NOT quedar sin
administradores vigentes (RN-05).

#### Scenario: Revocarse a sí mismo
- **WHEN** `admin@example.com` pide `DELETE /usuarios/1/roles/ADMIN`
- **THEN** responde 409

### Requirement: Cambio obligatorio de contraseña
Mientras `debe_cambiar_password` sea verdadero, el usuario SHALL poder usar sólo `/auth` y
`/health` (RN-06). Al cambiar la contraseña, las sesiones emitidas antes SHALL dejar de valer,
aunque sean del mismo segundo; la que devuelve el propio cambio no (RN-07).

#### Scenario: Cambio y cookie vieja
- **WHEN** `nuevo@example.com` inicia sesión, cambia la contraseña sin esperar y usa la cookie anterior
- **THEN** la cookie anterior da 401 y la nueva funciona
