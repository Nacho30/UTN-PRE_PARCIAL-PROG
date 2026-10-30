# contratos Specification

## Purpose
Especifica los contratos de entrada y salida de la API del taller mecánico separados de los modelos de tabla: entradas estrictas (`extra="forbid"`) sin exponer `password_hash`, `PATCH` parcial (`exclude_unset`), listados paginados `{items, total, page, size, pages}`, búsqueda de repuestos por descripción con parámetros ligados y manejo de errores que impide que entradas inválidas terminen en `500` (RN-18).

## Requirements

### Requirement: Contratos estrictos y separados
Los contratos de entrada SHALL estar separados de los modelos de tabla y SHALL rechazar los
campos no declarados (`extra="forbid"`). Ninguna respuesta MUST incluir `password_hash`.

#### Scenario: Registro con un rol
- **WHEN** `POST /auth/registro` trae `"rol": "ADMIN"`
- **THEN** responde 422 y no se crea nada

#### Scenario: PATCH del stock
- **WHEN** `PATCH /repuestos/1` trae `{"stock": 999}`
- **THEN** responde 422 y el stock no cambia

### Requirement: PATCH parcial
Los PATCH SHALL aplicar sólo los campos enviados (`exclude_unset`).

#### Scenario: Sólo la descripción
- **WHEN** `PATCH /repuestos/1` trae sólo `descripcion`
- **THEN** cambia la descripción y el precio queda igual

### Requirement: Listados paginados
Los listados SHALL devolver `{items, total, page, size, pages}`. `page` empieza en 1, `size`
va de 1 a 100 (por defecto 20). `total` SHALL contarse con los mismos filtros que la página.
Con cero resultados hay una página vacía.

#### Scenario: Página inexistente
- **WHEN** hay 4 repuestos y se pide `GET /repuestos?size=2&page=3`
- **THEN** responde 422 con «La página 3 no existe: hay 2»

#### Scenario: Tamaño fuera de rango
- **WHEN** se pide `size=500`
- **THEN** responde 422

### Requirement: Búsqueda con parámetros ligados
La búsqueda de repuestos por descripción SHALL usar parámetros ligados; el texto del usuario
MUST NOT concatenarse en el SQL.

#### Scenario: Inyección
- **WHEN** se busca `q=' OR '1'='1`
- **THEN** responde 200 con `items` vacío y `total` 0

### Requirement: Ninguna entrada inválida en 500
Ningún error SHALL devolver texto interno de la base; ninguna entrada inválida SHALL
terminar en 500 (RN-18).

#### Scenario: Parámetro de ruta no entero
- **WHEN** con sesión iniciada se pide `GET /ordenes/abc`
- **THEN** responde 422 sin ejecutar el handler
