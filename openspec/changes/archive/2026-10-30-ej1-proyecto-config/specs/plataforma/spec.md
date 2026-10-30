## ADDED Requirements

### Requirement: Configuración desde el entorno sin secretos por defecto
La aplicación SHALL leer su configuración con una clase `Settings` de pydantic-settings,
desde variables de entorno o un archivo `.env` no versionado. La URL de la base SHALL
armarse con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y
`POSTGRES_PORT` mediante un `@computed_field`, con driver asincrónico. `POSTGRES_PASSWORD`
y `JWT_SECRET` MUST NOT tener valor por defecto en el código.

#### Scenario: Falta la clave de firma
- **WHEN** se arranca la aplicación sin `JWT_SECRET` en el entorno
- **THEN** la validación de `Settings` falla y la aplicación no arranca

#### Scenario: Contraseña con caracteres especiales
- **WHEN** `POSTGRES_PASSWORD` contiene `@` o `/`
- **THEN** la URL generada los escapa y la conexión funciona

### Requirement: Recursos creados en el lifespan
El motor asincrónico (con el pool declarado en la configuración) y la fábrica de sesiones
SHALL crearse en el lifespan y guardarse en `app.state`, nunca al importar un módulo. El
lifespan SHALL calcular una vez el hash ficticio del login y, al apagar, cerrar el motor
con `dispose()`.

#### Scenario: Una sesión por petición
- **WHEN** llega una petición que usa `get_session`
- **THEN** recibe una sesión nueva creada con `expire_on_commit=False` a partir de
  `app.state.session_factory`, que se cierra al terminar la petición

### Requirement: Sondas de salud
El sistema SHALL exponer `GET /health/live`, que no toca la base, y `GET /health/ready`,
que ejecuta `SELECT 1`.

#### Scenario: Base caída
- **WHEN** la base no contesta y se pide `GET /health/ready`
- **THEN** responde 503 con un mensaje propio, mientras `GET /health/live` sigue en 200
