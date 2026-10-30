# Ejercicio 5 · Autorización

## Why
Los roles que trae el token son una foto del momento del login. Si se decide con ellos,
revocar un rol no le saca el permiso a una sesión abierta. La autorización se decide con los
roles vigentes **en la base** en cada petición (RN-04).

## What Changes
- `get_usuario_actual`: 401 sin cookie, token inválido o vencido, usuario inexistente o
  inactivo, o token anterior al último cambio de contraseña (RN-07, `iat` sin truncar).
- `requiere_rol(*roles)`: 403, consultando `asignacion_rol` en cada petición.
- Asignar rol con vencimiento opcional (con zona y futuro, si no 422); reasignar un rol vencido
  cierra la fila anterior y abre una nueva. Revocar escribe `revocada_en`, nunca borra.
- Autoprotección (RN-05): un ADMIN no se revoca su ADMIN y nunca quedan cero ADMIN vigentes.
- Dos grupos de rutas en `main.py`: abierto (`/health`, `/auth`) y protegido, con
  `exigir_password_al_dia` montado una sola vez (RN-06).
- Lo propio (`/mis-vehiculos`, `/mis-ordenes`, detalle y cancelación por el dueño) sólo pide
  estar autenticado (RN-17).
- `evento_seguridad`: altas, cambios de rol, cambios de contraseña y la carga inicial con
  actor `SISTEMA`.

## Impact
- Capabilities: `autorizacion`.
- Archivos: `app/core/dependencies.py`, `main.py`, `app/modules/usuarios/*`.
