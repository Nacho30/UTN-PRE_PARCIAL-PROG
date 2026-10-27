# Calidad

## Definición de terminado (de cada ejercicio)

Un *change* se da por terminado cuando:

1. Todas las tareas de su `tasks.md` están marcadas.
2. Cada escenario de su `specs/**/spec.md` se demostró (caso `.http`, `psql` o revisión).
3. El proyecto levanta desde cero siguiendo el README.
4. `alembic upgrade head` sobre una base vacía funciona, y también `downgrade base` y otra vez
   `upgrade head`; `alembic check` no detecta diferencias.
5. Ninguna entrada inválida del ejercicio termina en 500.
6. No hay secretos en el repositorio.
7. El roadmap y el estado de las reglas en el discovery están actualizados.
8. El prompt usado con IA quedó en `docs/prompts.md` (sólo la versión prolija).
9. Hay un commit con el ejercicio.

## Verificación por tipo

| Qué | Cómo |
|---|---|
| Arranque y configuración | `fastapi dev main.py`; sin `JWT_SECRET` no arranca |
| Salud | `/health/live` 200; `/health/ready` 200, y 503 con la base apagada |
| Esquema | Migraciones ida, vuelta, ida; `alembic check` |
| Sólo agregado | `psql -f test/solo_agregado.sql` |
| Endpoints | `test/*.http` con REST Client, después de `python seed.py` |
| Consultas fijas | `SQL_ECHO=true` y comparar el detalle con 2 y con 4 ítems |
| Estilo | `ruff check .` (opcional) |

## Evidencias de la entrega final

- Captura de la consola para **C-15**.
- Captura de `psql` para **C-14**.
- Se guardan en `docs/evidencias/`.

## Criterios de evaluación (peso)

| Criterio | Peso |
|---|---|
| Proyecto, configuración y ciclo de vida | 8 % |
| Modelos, relaciones y migraciones | 14 % |
| Contratos y CRUD | 10 % |
| Autenticación | 16 % |
| Autorización | 14 % |
| Repositorios y Unit of Work | 20 % |
| Integridad | 10 % |
| Lecturas sin N+1 y asincronía | 8 % |
