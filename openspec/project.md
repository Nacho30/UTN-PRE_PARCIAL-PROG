# Proyecto: API del taller mecánico

TP de Programación III (UTN, Tecnicatura Universitaria en Programación), unidades 1 a 6.
Se desarrolla con **SDD (Spec-Driven Development)** usando OpenSpec: cada ejercicio de la
consigna es un *change* en `openspec/changes/<ejN-...>/` con su propuesta, sus tareas y el
delta de specs. Al terminar un ejercicio se archiva con `openspec archive <change>`, que
mueve el delta a `openspec/specs/`.

## Mapa de la documentación

- [Discovery](discovery/README.md): qué se construye y por qué.
- [Foundations](foundations/README.md): cómo se construye.
- [Roadmap](roadmap.md): en qué orden y en qué estado está cada ejercicio.
- [Changes](changes): un change por ejercicio.
- [Specs](specs/README.md): requisitos vigentes, al archivar.

## Propósito

API REST asincrónica para el trabajo diario de un taller: recepción da de alta clientes,
vehículos y órdenes de trabajo; el mecánico las inicia y las termina (descontando stock);
el administrador mantiene repuestos, stock y roles; los clientes se registran solos y
consultan lo propio.

## Stack

| Componente | Versión mínima |
|---|---|
| Python | 3.12 |
| FastAPI | 0.111 (`async def` en todos los handlers) |
| SQLModel | 0.0.24 |
| SQLAlchemy | 2.0 asincrónico |
| asyncpg | 0.30 |
| PostgreSQL | 16 |
| Alembic | 1.13, plantilla asincrónica |
| pydantic-settings | 2.0 |
| bcrypt | 4.0 |
| PyJWT | 2.8 |

## Convenciones

- Capas: **Router → Service → UoW → Repository → Model**. Cada capa sabe lo suyo:
  - el router construye el Unit of Work con una dependencia, llama al servicio y traduce
    los errores de dominio a HTTP (`route_class=RutaDeDominio`);
  - el servicio aplica las reglas de negocio y abre el UoW con `async with`, nunca lo
    construye;
  - el UoW confirma o revierte al salir del bloque y no cierra la sesión;
  - los repositorios hacen `flush()`, nunca `commit()`, y declaran la precarga.
- Organización por módulo funcional: `health`, `usuarios`, `clientes`, `repuestos`, `ordenes`.
- Nombres de tablas y columnas: los de la consigna, sin renombrar.
- Fechas `timestamptz`; dinero `NUMERIC` / `Decimal`, nunca `float`.
- Mensajes de error propios en castellano; nunca texto de la base ni trazas.
- Las restricciones de nombres predecibles (`naming_convention`) permiten traducir cada
  `IntegrityError` a un 409 con mensaje propio.
- Secretos sólo en el entorno (`.env`, no versionado). Sin valores por defecto.
