# Tareas · Ejercicio 5

## 1. Dependencias
- [ ] 1.1 `get_usuario_actual` con todas las causas de 401
- [ ] 1.2 Comparación de `iat` con `password_cambiada_en` en microsegundos enteros
- [ ] 1.3 `get_roles_vigentes` desde `asignacion_rol` (no revocada, ya empezada, sin vencer)
- [ ] 1.4 `requiere_rol(*roles)` → 403
- [ ] 1.5 `exigir_password_al_dia` → 403 con el cambio pendiente

## 2. Grupos de rutas
- [ ] 2.1 Grupo abierto: `health` y `auth`
- [ ] 2.2 Grupo protegido con el control montado una sola vez

## 3. Roles
- [ ] 3.1 `POST /usuarios` (alta de personal con contraseña provisoria y cambio obligatorio)
- [ ] 3.2 `GET /usuarios/{id}/roles` (historial completo, con `vigente`)
- [ ] 3.3 `POST /usuarios/{id}/roles` (vencimiento con zona y futuro; reasignación de vencidos)
- [ ] 3.4 `DELETE /usuarios/{id}/roles/{rol}` con autoprotección (RN-05)
- [ ] 3.5 `POST /auth/cambiar-password` (invalida sesiones previas; devuelve cookie nueva)
- [ ] 3.6 `GET /eventos` paginado
