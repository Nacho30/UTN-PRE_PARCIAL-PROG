# Diseño · Repositorios y Unit of Work

## Quién crea, abre, confirma y cierra

| Pieza | Crea | Abre | Confirma / revierte | Cierra |
|---|---|---|---|---|
| Sesión | `get_session` (desde `app.state.session_factory`) | — | — | `get_session`, al terminar la petición |
| Unit of Work | dependencia `get_<módulo>_uow` del router | el servicio, con `async with` | `UnitOfWork.__aexit__` | nunca (no creó la sesión) |
| Repositorio | el UoW del módulo, con la misma sesión | — | nunca (sólo `flush`) | — |

La única excepción es `AccesoUnitOfWork` (intentos de login): crea su propia sesión desde la
fábrica, la confirma siempre y la cierra, porque el fallo que se quiere contar es el mismo que
revierte la transacción de la petición (sección 6.8.1).

## Terminar una orden (RN-13), un solo bloque

```
async with uow:
    orden = ordenes.get_con_items(id)            # precarga ítems
    permiso (403) → estado EN_REPARACION (409)
    por cada ítem:
        stock.mover(repuesto, -cantidad, "Orden N")   # UPDATE condicionado + movimiento
            └─ si no alcanza → StockInsuficiente (409) → rollback de TODO
    orden.estado = TERMINADA
    historial.add(EN_REPARACION → TERMINADA)
# commit
```

Cuatro clases de escritura (repuesto, movimiento_stock, orden_trabajo, historial_estado_orden)
en una sola transacción.

## Lecturas de autorización y la conexión
Las dependencias de autorización leen dentro de `lectura_corta(session)`, que confirma la
transacción de lectura al salir y devuelve la conexión al pool. Así, el `cambiar-password`
puede verificar y calcular bcrypt sin una conexión tomada.
