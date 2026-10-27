# Flujo SDD

Cada ejercicio de la consigna se trabaja como un *change* de OpenSpec. Nunca se escribe código
sin un *change* aprobado.

```
discovery ─▶ foundations ─▶ roadmap ─▶ change (proposal → design → specs → tasks)
                                          │
                                          ▼
                                       apply (código) ─▶ verify ─▶ archive ─▶ specs vigentes
```

## Pasos por ejercicio

| Paso | Qué se hace | Dónde |
|---|---|---|
| 1. Elegir | Tomar el próximo ejercicio del roadmap cuyas dependencias estén terminadas | `openspec/roadmap.md` |
| 2. Proponer | Por qué, qué cambia, qué capacidades y archivos toca | `changes/<ej>/proposal.md` |
| 3. Diseñar | Sólo si hay decisiones técnicas que explicar (flujos, orden, transacciones) | `changes/<ej>/design.md` |
| 4. Especificar | Requisitos con `SHALL`/`MUST` y escenarios `WHEN`/`THEN` | `changes/<ej>/specs/<capacidad>/spec.md` |
| 5. Planificar | Tareas chicas, verificables y en orden | `changes/<ej>/tasks.md` |
| 6. Validar | `openspec validate <ej> --strict` | — |
| 7. Implementar | Código siguiendo foundations; marcar cada tarea al terminarla | `app/`, `migrations/`, `test/` |
| 8. Verificar | Demostrar cada escenario; cumplir la definición de terminado | `foundations/calidad.md` |
| 9. Archivar | `openspec archive <ej>`: el delta pasa a `openspec/specs/` | `openspec/specs/` |
| 10. Cerrar | Actualizar roadmap, estado de reglas, `docs/prompts.md`; commit | — |

## Comandos de OpenSpec

```bash
npm install -g @fission-ai/openspec     # una vez
openspec list                            # changes en curso
openspec show <change>                   # ver un change
openspec validate <change> --strict      # validar formato
openspec archive <change>                # archivar al terminar
```

## Formato de un spec

```markdown
## ADDED Requirements

### Requirement: <nombre>
El sistema SHALL <comportamiento>.

#### Scenario: <nombre>
- **WHEN** <condición>
- **THEN** <resultado>
```

Se usa `## MODIFIED Requirements` cuando un *change* posterior cambia un requisito ya archivado.

## Trabajo con IA

- El agente lee primero `AGENTS.md`, `openspec/project.md`, el discovery y las foundations.
- Se le pide **un** *change* por vez, nunca «todo el TP».
- El prompt prolijo se guarda en `docs/prompts.md`.
