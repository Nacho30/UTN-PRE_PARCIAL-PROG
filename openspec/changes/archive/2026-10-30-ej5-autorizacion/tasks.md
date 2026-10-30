# Tareas · Ejercicio 5

## 1. Dependencias
- [x] 1.1 `get_usuario_actual` con todas las causas de 401
- [x] 1.2 Comparación de `iat` con `password_cambiada_en` en microsegundos enteros
- [x] 1.3 `get_roles_vigentes` desde `asignacion_rol` (no revocada, ya empezada, sin vencer)
- [x] 1.4 `requiere_rol(*roles)` → 403
- [x] 1.5 `exigir_password_al_dia` → 403 con el cambio pendiente

## 2. Grupos de rutas
- [x] 2.1 Grupo abierto: `health` y `auth`
- [x] 2.2 Grupo protegido con el control montado una sola vez

## 3. Roles
- [x] 3.1 `POST /usuarios` (alta de personal con contraseña provisoria y cambio obligatorio)
- [x] 3.2 `GET /usuarios/{id}/roles` (historial completo, con `vigente`)
- [x] 3.3 `POST /usuarios/{id}/roles` (vencimiento con zona y futuro; reasignación de vencidos)
- [x] 3.4 `DELETE /usuarios/{id}/roles/{rol}` con autoprotección (RN-05)
- [x] 3.5 `POST /auth/cambiar-password` (invalida sesiones previas; devuelve cookie nueva)
- [x] 3.6 `GET /eventos` paginado
