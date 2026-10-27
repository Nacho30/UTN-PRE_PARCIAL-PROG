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
