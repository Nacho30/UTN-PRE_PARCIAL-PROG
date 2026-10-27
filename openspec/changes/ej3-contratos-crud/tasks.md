# Tareas · Ejercicio 3

## 1. Contratos
- [x] 1.1 Base `EntradaEstricta` con `extra="forbid"`
- [x] 1.2 Tipos acotados reutilizables: `IdEntero`, `IdPath`, `texto(n)`, `Dinero`
- [x] 1.3 Esquemas de entrada y salida por módulo; salida de usuario sin `password_hash`
- [x] 1.4 PATCH de repuesto sólo con `descripcion` y `precio`; `stock` da 422

## 2. Paginación
- [x] 2.1 `Pagina[T]` genérica con `items, total, page, size, pages`
- [x] 2.2 `ParametrosPagina` como dependencia (`page`, `size`)
- [x] 2.3 `pages = max(1, ceil(total / size))`; página fuera de rango → 422 «La página N no existe: hay M»

## 3. CRUD
- [x] 3.1 Clientes y vehículos (alta, detalle, baja lógica)
- [x] 3.2 Repuestos (listado con `q`, detalle, alta con `stock_inicial`, PATCH, baja, reposición, movimientos, precios)
- [x] 3.3 Órdenes (alta, listado por `estado`, detalle)
- [x] 3.4 Traducción de `IntegrityError` por nombre de restricción a 409 con mensaje propio
- [x] 3.5 Manejador final para errores no previstos: 500 genérico sin traza
