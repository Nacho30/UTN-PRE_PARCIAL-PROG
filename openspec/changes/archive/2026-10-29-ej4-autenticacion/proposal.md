# Ejercicio 4 · Autenticación

## Why
La autenticación tiene que ser segura sin frenar el servidor (bcrypt es lento a propósito) y
sin revelar qué cuentas existen (RN-08, RN-09).

## What Changes
- bcrypt con costo `BCRYPT_ROUNDS` en la configuración; cada llamada corre en
  `asyncio.to_thread` y bajo un semáforo (`BCRYPT_CONCURRENCIA`).
- El hash se calcula **antes** de abrir la transacción.
- Todo campo que termina en bcrypt acepta como máximo 72 **bytes** UTF-8 (422 si pasa).
- Login en este orden: 1) límite de intentos (una consulta; 429 con `Retry-After` sin calcular
  hash), 2) verificación contra el hash del usuario o contra el hash ficticio.
- JWT con `sub`, `iat` (con fracción de segundo), `exp` y `roles` vigentes al emitirlo.
- El token viaja sólo en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`,
  `Secure` configurable). El cuerpo del login no lo trae.
- `POST /auth/registro` (RN-02), `POST /auth/logout`, `GET /auth/yo`.

## Impact
- Capabilities: `autenticacion`.
- Archivos: `app/core/security.py`, `app/modules/usuarios/{schemas,service,router}.py`.
