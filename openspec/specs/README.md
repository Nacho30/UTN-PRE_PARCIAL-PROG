# Specs vigentes

Acá viven los requisitos **ya construidos y archivados**. Esta carpeta no se edita a mano: se
llena con `openspec archive <change>`, que mueve el delta de `changes/<change>/specs/` a
`specs/<capacidad>/spec.md` y el change a `changes/archive/`.

Capacidades previstas (una por change):

| Capacidad | Change que la crea |
|---|---|
| `plataforma` | ej1-proyecto-config |
| `esquema` | ej2-modelos-migraciones |
| `contratos` | ej3-contratos-crud |
| `autenticacion` | ej4-autenticacion |
| `autorizacion` | ej5-autorizacion |
| `persistencia` | ej6-repositorios-uow |
| `integridad` | ej7-integridad |
| `lecturas` | ej8-lecturas-asincronia |

Mientras un change no se archiva, sus requisitos se leen en `changes/<change>/specs/`.
