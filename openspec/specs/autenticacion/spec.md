# autenticacion Specification

## Purpose
Especifica la autenticación de usuarios del taller mecánico: hash de contraseñas con bcrypt sin bloquear el bucle de eventos y con validación de límite de 72 bytes UTF-8, auto-registro atómico de clientes en un único Unit of Work (RN-02), control de intentos de login por ventana temporal con `Retry-After` (RN-08), login indistinguible en mensaje y tiempo ante correos inexistentes mediante hash ficticio (RN-09), y manejo de sesión mediante JWT exclusivamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`).

## Requirements

### Requirement: Hash de contraseñas sin bloquear el bucle
Las contraseñas SHALL guardarse con bcrypt y un costo declarado en la configuración. Toda
llamada a bcrypt SHALL correr en `asyncio.to_thread` y bajo un semáforo. El hash SHALL
calcularse antes de abrir la transacción.

#### Scenario: Contraseña de más de 72 bytes
- **WHEN** se registra una contraseña de 40 «ñ» (80 bytes)
- **THEN** responde 422, no 500

### Requirement: Auto-registro atómico
`POST /auth/registro` SHALL crear el usuario, su asignación CLIENTE y su ficha de cliente en un
único Unit of Work (RN-02).

#### Scenario: Documento de un cliente existente
- **WHEN** el documento ya pertenece a un cliente del taller
- **THEN** responde 409 con mensaje propio y no queda ninguna fila nueva

#### Scenario: Correo repetido
- **WHEN** el correo ya está registrado
- **THEN** responde 409 «El correo ya está registrado»

### Requirement: Límite de intentos
Después de 5 intentos fallidos con el mismo correo desde la misma IP en 60 segundos, el login
SHALL responder 429 con `Retry-After` sin verificar la contraseña. Un login correcto reinicia
la cuenta (RN-08).

#### Scenario: Sexto intento
- **WHEN** se hacen seis logins fallidos seguidos
- **THEN** el sexto responde 429 con `Retry-After` en pocos milisegundos y hay cinco filas con `exito = false` en `intento_acceso`

### Requirement: Login indistinguible
El login SHALL responder el mismo cuerpo y tardar lo mismo exista o no el correo (RN-09).

#### Scenario: Correo inexistente
- **WHEN** se hace login con un correo que no existe
- **THEN** responde 401 «Correo o contraseña incorrectos» tras verificar contra el hash ficticio

### Requirement: Token sólo en cookie
El JWT SHALL llevar `sub`, `iat`, `exp` y los roles vigentes al emitirlo, y viajar sólo en la
cookie `access_token` con `HttpOnly`, `SameSite=Lax` y `Max-Age` igual a la duración del
token. El cuerpo del login MUST NOT traer el token, y la cabecera `Authorization` MUST NOT
leerse.

#### Scenario: Bearer en vez de cookie
- **WHEN** se llama a `GET /auth/yo` con `Authorization: Bearer <token>` y sin cookie
- **THEN** responde 401
