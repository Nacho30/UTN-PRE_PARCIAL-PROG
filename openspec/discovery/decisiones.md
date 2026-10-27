# Decisiones y preguntas abiertas

Donde la consigna deja margen, la decisión queda escrita acá con su razón. Si una decisión
cambia, se actualiza este archivo y el spec afectado.

## Decisiones tomadas

| # | Tema | Decisión | Razón |
|---|---|---|---|
| D-01 | Driver de la base | `postgresql+asyncpg` por defecto; `POSTGRES_DRIVER` permite psycopg 3 | La consigna acepta los dos |
| D-02 | Nombres de restricciones | `naming_convention` en la metadata (`uq_`, `ck_`, `fk_`, `ix_`, `pk_`) | Nombres predecibles para traducir cada `IntegrityError` a un 409 propio |
| D-03 | Carga perezosa | `lazy="raise_on_sql"` en todas las relaciones | Una precarga faltante falla en vez de esconder una consulta |
| D-04 | Columna extra `otorgada_por` | FK nula a `usuario.id` | La consigna la lista; nulo para la carga inicial (actor SISTEMA) |
| D-05 | `evento_seguridad.actor` | Texto, no FK | El actor puede ser `SISTEMA` (sección 5.8) |
| D-06 | Normalización | Patente y código en mayúsculas sin espacios ni guiones; correo en minúsculas | Evita duplicados que la base no vería |
| D-07 | Stock inicial en `seed.py` | Se carga con su movimiento «Stock inicial»; desde el ej6, por el punto único | RN-14 y datos iniciales de la consigna |
| D-08 | Intento bloqueado (429) | No se anota en `intento_acceso` | No llegó a verificarse; anotarlo correría la ventana y `Retry-After` mentiría |
| D-09 | `Retry-After` | `ceil(quinto_fallo + 60 s − ahora)`, mínimo 1 | El quinto fallo es el que tiene que salir de la ventana |
| D-10 | Lecturas de autorización | Transacción corta que devuelve la conexión al pool | El servicio no tiene la conexión tomada mientras corre bcrypt |
| D-11 | Vaciado en `seed.py` | `TRUNCATE ... RESTART IDENTITY CASCADE` | TRUNCATE no dispara los triggers de fila de sólo agregado |
| D-12 | Errores de dominio | Los servicios lanzan errores propios y una `route_class` los traduce a HTTP | El servicio no conoce HTTP; el router traduce (estructura obligatoria) |

## Preguntas abiertas

| # | Pregunta | A quién | Impacto |
|---|---|---|---|
| P-01 | ¿Qué es exactamente «active stack» que pidió el profesor? | Profesor | Puede cambiar la forma de los artefactos SDD |
| P-02 | ¿Hay que archivar cada change (`openspec archive`) al cerrar el ejercicio, o se entregan sin archivar? | Profesor | Dónde quedan los specs vigentes |
