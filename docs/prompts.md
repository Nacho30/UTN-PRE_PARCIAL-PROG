# Prompts usados con IA

## TP Unidades 1 a 6 · Taller mecánico · Ejercicios 1 y 2

> Leé la consigna adjunta (TP «Taller mecánico: órdenes de trabajo, stock y acceso con FastAPI
> y PostgreSQL», Programación III) y el diagrama de clases. Desarrollá los ejercicios 1 y 2 con
> SDD usando OpenSpec: primero un *change* por ejercicio (propuesta, tareas y delta de specs
> con escenarios) y después el código.
>
> Ejercicio 1: la estructura obligatoria del proyecto completa (los archivos de ejercicios
> posteriores pueden quedar como esqueleto), `Settings` con pydantic-settings y la URL de la
> base como `@computed_field`, sin valores por defecto para la contraseña de la base ni la clave
> de firma; motor y fábrica de sesiones creados en el lifespan y guardados en `app.state`;
> `get_session` con `expire_on_commit=False`; hash ficticio calculado en el lifespan; `dispose()`
> al apagar; `GET /health/live` y `GET /health/ready` (503 si la base no contesta).
>
> Ejercicio 2: los modelos con los nombres de tablas y columnas de la consigna, todas sus
> restricciones, los tres índices únicos parciales, el catálogo `estado_orden` con clave
> foránea, navegación en ambos extremos, `Usuario.cliente` como objeto y un índice por clave
> foránea. Esquema sólo con Alembic (plantilla asincrónica): una migración autogenerada con
> todas las tablas y otra escrita a mano con el disparador de sólo agregado, cada una con un
> comentario que diga que se leyó antes de aplicarla. Incluí `seed.py`, `env.example`,
> `requirements.txt`, `test/solo_agregado.sql` y un README con los pasos para levantarlo.

## Artefactos SDD: discovery, foundations y roadmap

> Con la consigna del TP y el diagrama de clases, prepará la capa documental de SDD en
> `openspec/`: un **discovery** (contexto y actores, dominio con diagrama y glosario, reglas de
> negocio RN-01 a RN-20 con su garante y su ejercicio, requisitos no funcionales, endpoints de
> referencia, casos C-01 a C-19 y decisiones con preguntas abiertas), unas **foundations**
> (stack, arquitectura en capas con quién crea, abre, confirma y cierra, convenciones,
> seguridad, definición de terminado y el flujo SDD con OpenSpec) y un **roadmap** con el orden
> de los ejercicios, sus dependencias, hitos y estado. Dejá los *changes* de los ejercicios 3 a
> 8 especificados y con sus tareas pendientes, sin tocar el código, y un `AGENTS.md` con las
> reglas para trabajar con IA.


## TP Unidades 1 a 6 · Taller mecánico · Ejercicio 3

> Implementá el Ejercicio 3 (Contratos y CRUD) del TP siguiendo estrictamente SDD, OpenSpec
> y el modo Strict TDD.
>
> Tareas implementadas:
> - Base `EntradaEstricta` con `extra="forbid"` y `str_strip_whitespace=True`.
> - Tipos acotados reutilizables: `IdEntero`, `IdPath`, `texto(n)` sin `\x00`, `Dinero`, normalización de patentes/codes/emails, y límite de 72 bytes UTF-8 para contraseñas.
> - Esquemas DTO de entrada y salida por módulo (`usuarios`, `clientes`, `repuestos`, `ordenes`), garantizando que ninguna respuesta exponga `password_hash`.
> - `PATCH /repuestos/{id}` parcial sólo con `descripcion` y `precio` (`exclude_unset`), rechazando `stock` y `null` explícito con 422, y registrando `HistorialPrecio` en la misma transacción si el precio cambia (RN-20).
> - Paginación con envoltorio `{items, total, page, size, pages}`, cálculo de páginas y validación de rango (422 si la página no existe).
> - CRUD completo con arquitectura en capas (`Router -> Service -> UoW -> Repository -> Model`):
>   - Clientes y vehículos (alta, detalle con vehículos vigentes precargados, baja lógica con verificación de órdenes abiertas RN-16).
>   - Repuestos (búsqueda con parámetros ligados e `ILIKE` escapado, alta con stock inicial y movimiento, reposición, movimientos, precios).
>   - Órdenes (alta con precios unitarios copiados de repuestos y cálculo de total en el servidor RN-10, catálogo de estados ordenado por posición, iniciar, terminar con descuento de stock y rollback total si no alcanza RN-13, cancelar).
> - Traducción de `IntegrityError` a 409 con mensaje legible en castellano sin exponer SQL ni detalles de la base (RN-18).
> - Manejador 500 genérico sin traza en la respuesta.

## TP Unidades 1 a 6 · Taller mecánico · Ejercicio 4

> Implementá el Ejercicio 4 (Autenticación) del TP siguiendo estrictamente SDD, OpenSpec y el modo Strict TDD.
>
> Tareas a implementar:
> - Funciones de hash (`hash_password` y `verificar_password`) asincrónicas usando `asyncio.to_thread` bajo un semáforo (`BCRYPT_CONCURRENCIA`) y costo configurable (`BCRYPT_ROUNDS`).
> - Cálculo del hash **antes** de abrir la transacción de base de datos.
> - Tipo o validador para campos terminados en bcrypt (`PasswordBcrypt`) que limite a un máximo de 72 bytes UTF-8 (retornando 422 si se excede, considerando que una «ñ» ocupa dos bytes).
> - Orden estricto del login (RN-08, RN-09): 1) verificación de límite de intentos sobre `intento_acceso` (1 consulta; responde 429 con `Retry-After` sin calcular ningún hash si se superó el límite de 5 intentos fallidos en 60 segundos), 2) verificación contra el hash del usuario o contra un hash ficticio si el correo no existe, tardando lo mismo.
> - Emisión de JWT con `sub`, `iat` (con fracción de segundo para soportar precisión sin truncar), `exp` y los roles vigentes al emitirlo.
> - Cookie `access_token` segura: `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la duración del token y `Secure` configurable desde la configuración, sin incluir el token en el cuerpo de la respuesta del login.
> - Endpoints de autenticación: `POST /auth/registro` (creando usuario, rol CLIENTE y ficha de cliente en un único UoW según RN-02), `POST /auth/login`, `POST /auth/logout` (borrando la cookie) y `GET /auth/yo` (devolviendo el usuario, sus roles vigentes en base y los que dice el token).

## Archivo del change `ej4-autenticacion`
- Change archivado exitosamente mediante OpenSpec (`openspec archive ej4-autenticacion --yes`).




## Ejercicio 5 · Autorización (Active Stack / OPSX)

> Revisá el código existente y la consigna; aplicá únicamente `ej5-autorizacion` con TDD:
> identidad desde cookie, roles vigentes en base, control de contraseña en el grupo protegido,
> administración de personal/roles/eventos, contraseña con invalidación inmediata y acceso
> propio. Conservá los contratos existentes y registrá las extensiones nuevas. Probá los
> escenarios con PostgreSQL aislado y savepoints, validá y archivá el change, y dejá un commit
> local para revisión. No hagas push ni PR hasta la confirmación del usuario.
## 2026-10-30 · Ejercicio 6

Pedido: completar el punto 6 con Active Stack, pruebas antes del código y commit separado,
sin push ni PR hasta revisión. Se reutilizó `ej6-repositorios-uow`, conservando los
repositorios ya correctos y completando UoW inyectados, stock centralizado y atomicidad.
Documento real obligatorio y teléfono opcional como el contrato existente de clientes;
personal conserva su propio contrato. Evidencia en `docs/validacion-ej5-ej6.md`.
