# Casos de prueba mínimos

Archivos `.http` en `test/` (extensión REST Client), cada pedido con la respuesta esperada en un
comentario, y `test/solo_agregado.sql` para C-14. **Antes de cada archivo: `python seed.py`.**

Varias sesiones a la vez: cada login se nombra con `# @name`, y sus pedidos llevan
`# @no-cookie-jar` y `Cookie: {{loginAdmin.response.headers.Set-Cookie}}`.

| Caso | Qué se demuestra | Resultado esperado | Archivo previsto | Habilita |
|---|---|---|---|---|
| C-01 | Parámetro de ruta no entero, con sesión | 422, sin ejecutar el handler | `test/01_auth_y_contratos.http` | ej3 + ej4 |
| C-02 | Registro; correo y documento repetidos | 201; 409 propio; el rechazado no deja filas | `test/01_auth_y_contratos.http` | ej4 + ej6 |
| C-03 | La cookie del login | `Set-Cookie` HttpOnly, SameSite=Lax, Max-Age; cuerpo sin token; sin cookie o con Bearer, 401 | `test/01_auth_y_contratos.http` | ej4 |
| C-04 | Correo existente con contraseña mala, y correo inexistente | 401 mismo cuerpo, tiempo parecido | `test/01_auth_y_contratos.http` | ej4 |
| C-05 | Seis fallos seguidos | El sexto, 429 con `Retry-After` en pocos ms; los cinco fallos en `intento_acceso` | `test/01_auth_y_contratos.http` | ej4 + ej7 |
| C-06 | 401 contra 403, y lo propio | Sin rol 403; el cliente ve su orden (200) y no la ajena (403) | `test/02_autorizacion.http` | ej5 |
| C-07 | Revocar con la sesión abierta; vencimientos inválidos | Misma cookie → 403; `/auth/yo` muestra la diferencia; la fila sigue; vencimiento pasado o sin zona → 422 | `test/02_autorizacion.http` | ej5 |
| C-08 | Autoprotección | El admin no se revoca su ADMIN: 409 | `test/02_autorizacion.http` | ej5 |
| C-09 | Cambio obligatorio | 403 salvo `/auth`; tras el cambio, la cookie nueva vale y la anterior da 401, sin esperar | `test/02_autorizacion.http` | ej5 |
| C-10 | Alta de orden con dos ítems | 201 con precios copiados, total e historial; repuesto inexistente → 409 y no queda la orden | `test/03_ordenes.http` | ej3 + ej6 |
| C-11 | Terminar la orden 2 (4 bujías, hay 2) | 409; estado, stock, movimientos e historial intactos | `test/03_ordenes.http` | ej6 |
| C-12 | Reponer y terminar la orden 2 | 200; baja el stock; movimientos e historial; el aviso sale después de la respuesta | `test/03_ordenes.http` | ej6 + ej8 |
| C-13 | Cancelar | Dueño, pendiente → 200; ajena → 403; terminada → 409 | `test/03_ordenes.http` | ej3 + ej5 |
| C-14 | UPDATE y DELETE en las tablas de sólo agregado; orden con estado inexistente | Seis rechazos del disparador; el último, por la clave foránea | `test/solo_agregado.sql` ✅ | **ej2 (listo)** |
| C-15 | Detalle de una orden con 2 y con 4 ítems | La misma cantidad de consultas en la consola | `test/03_ordenes.http` | ej8 |
| C-16 | `' OR '1'='1`; paginación con filtro; PATCH parcial; PATCH del stock | Lista vacía, total 0; `q=freno&size=1` total 1 pages 1, `page=2` 422; `size=500` 422; sólo cambia lo enviado; stock → 422 | `test/04_repuestos_y_vehiculos.http` | ej3 |
| C-17 | Catálogo; filtrar por estado no declarado | Los cuatro por posición, TERMINADA y CANCELADA finales; sin sesión 401; 422 | `test/03_ordenes.http` | ej3 |
| C-18 | Cambiar el precio y después sólo la descripción | Una línea nueva en `/precios`; el segundo PATCH no agrega; recepción 403 | `test/04_repuestos_y_vehiculos.http` | ej3 + ej6 |
| C-19 | Baja de un vehículo sin órdenes y alta con la misma patente para otro cliente | 204 y 201; segunda patente vigente igual → 409 | `test/04_repuestos_y_vehiculos.http` | ej3 |

## Datos iniciales que usan los casos (`seed.py`)

| Qué | Datos |
|---|---|
| Catálogo | PENDIENTE (1), EN_REPARACION (2), TERMINADA (3, final), CANCELADA (4, final) |
| Usuarios | admin@ y admin2@ (ADMIN), recepcion@ (RECEPCION), mecanico@ y mecanico2@ (MECANICO), cliente@ (CLIENTE), nuevo@ (MECANICO, cambio obligatorio) |
| Clientes | Laura, con usuario cliente@ y dos vehículos; Jorge, sin usuario, con uno |
| Repuestos | Filtro (10), pastillas (4), bujía (2), aceite por litro (20), cada stock como movimiento «Stock inicial» |
| Órdenes | 1 PENDIENTE del primer vehículo de Laura; 2 EN_REPARACION del de Jorge, asignada a mecanico@, con 4 bujías cuando hay 2 |
| Historial de precios | Filtro de 8000 a 8500 |
| Historial de seguridad | Actor `SISTEMA`: «Carga de los datos iniciales» |
