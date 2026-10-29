# Tareas · Ejercicio 4

## 1. Seguridad
- [x] 1.1 `hash_password` y `verificar_password` asincrónicas: `to_thread` + semáforo
- [x] 1.2 Costo de bcrypt desde `Settings.BCRYPT_ROUNDS`
- [x] 1.3 `crear_token` con `iat` float (fracción de segundo), `exp` y `roles`
- [x] 1.4 `decodificar_token` con `require=["sub","iat","exp"]`

## 2. Contratos
- [x] 2.1 `PasswordBcrypt` (máx. 72 bytes) en registro, login, alta de personal y cambio
- [x] 2.2 Respuesta del login sin token

## 3. Endpoints
- [x] 3.1 `POST /auth/registro`: usuario + rol CLIENTE + cliente en un UoW, hash antes
- [x] 3.2 `POST /auth/login` en el orden del diseño
- [x] 3.3 Cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable
- [x] 3.4 `POST /auth/logout` borra la cookie
- [x] 3.5 `GET /auth/yo` con roles vigentes y roles del token
