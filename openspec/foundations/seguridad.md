# Seguridad

## Secretos

- `POSTGRES_PASSWORD` y `JWT_SECRET` sin valor por defecto: si faltan, la app no arranca.
  Una clave inventada al arrancar tampoco sirve (cambia en cada reinicio y dos procesos se
  rechazan los tokens).
- `alembic.ini` sin URL ni credenciales: `migrations/env.py` toma la URL de `Settings`.
- Las contraseñas de `seed.py` son de mentira y viven sólo ahí.

## Contraseñas

- bcrypt con costo `BCRYPT_ROUNDS` (configuración, no código).
- Toda llamada a bcrypt: `asyncio.to_thread` + semáforo (`BCRYPT_CONCURRENCIA`).
- El hash se calcula **antes** de abrir la transacción.
- Todo campo que termina en bcrypt —registro, login, alta de personal, actual y nueva del
  cambio— acepta como máximo **72 bytes UTF-8** (422 si pasa; una «ñ» ocupa dos).
- Hash ficticio calculado una vez en el lifespan, con el mismo costo (RN-09).

## Login (orden obligatorio)

1. Límite de intentos: una consulta sobre `intento_acceso`; si se superó, 429 con
   `Retry-After` **sin calcular ningún hash**.
2. Verificación contra el hash del usuario o contra el hash ficticio.
3. Anotar el intento en su **propia transacción**.
4. 401 «Correo o contraseña incorrectos», el mismo cuerpo exista o no el correo.

## Token

- JWT con `sub`, `iat` (**con fracción de segundo**), `exp` y los roles vigentes al emitirlo.
- Sólo en la cookie `access_token`: `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la duración,
  `Secure` configurable. El cuerpo del login no lo trae. La cabecera `Authorization` no se lee.
- Comparación `iat` contra `password_cambiada_en` en microsegundos enteros (RN-07).

## Autorización

- Los permisos se deciden con las filas vigentes de `asignacion_rol` en **cada petición**
  (RN-04); los roles del token son informativos.
- Revocar escribe `revocada_en`; la fila nunca se borra.
- Autoprotección: un admin no se revoca su ADMIN y nunca quedan cero admins vigentes (RN-05).
- Historial de seguridad: altas, cambios de rol y de contraseña, carga inicial con actor `SISTEMA`.

## Datos

- SQL siempre con parámetros ligados; la búsqueda con `ILIKE` escapa `%` y `_`.
- Ninguna respuesta incluye `password_hash`.
- Ningún mensaje al cliente trae texto de la base (RN-18).
