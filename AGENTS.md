# Instrucciones para agentes de IA

Este proyecto se desarrolla con **SDD (Spec-Driven Development)** y **OpenSpec**. Antes de
escribir código, leé en este orden:

1. [`openspec/project.md`](openspec/project.md): propósito, stack y convenciones generales.
2. [`openspec/discovery/`](openspec/discovery/README.md): qué hay que construir (dominio, reglas
   RN-01 a RN-20, endpoints, casos C-01 a C-19).
3. [`openspec/foundations/`](openspec/foundations/README.md): cómo se construye (capas,
   convenciones, seguridad, definición de terminado, flujo SDD).
4. [`openspec/roadmap.md`](openspec/roadmap.md): qué ejercicio sigue y de qué depende.
5. El *change* del ejercicio en curso: `openspec/changes/<change>/`.

## Reglas

- Trabajá **un change por vez**; no implementes nada que no esté en su `tasks.md`.
- Respetá los nombres de tablas y columnas de la consigna: no se renombran ni se quitan.
- Capas: Router → Service → UoW → Repository → Model. Ningún repositorio hace `commit()`;
  ningún servicio construye su Unit of Work; el Unit of Work no cierra la sesión.
- El esquema cambia **sólo** con una migración de Alembic; nunca `create_all`.
- Nada de secretos en el código, en `alembic.ini` ni en el repositorio.
- Marcá cada tarea al terminarla y, al cerrar el change, actualizá el roadmap, el estado de las
  reglas en `discovery/reglas-de-negocio.md` y `docs/prompts.md`.
- Al terminar un change: `openspec validate <change> --strict` y `openspec archive <change>`.
