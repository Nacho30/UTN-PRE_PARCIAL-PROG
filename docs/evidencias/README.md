# Evidencias

Lo que pide el formato de entrega, y algo más:

| Archivo | Caso | Cómo se obtiene |
|---|---|---|
| `C-14_psql_solo_agregado.txt` | C-14 | `psql -h localhost -U taller -d taller -f test/solo_agregado.sql` después de `python seed.py`: los seis rechazos del disparador y el de la clave foránea |
| `c14_solo_agregado.png` | C-14 | Captura aportada para la entrega: seis rechazos del disparador y uno de clave foránea |
| `C-15_consultas_detalle.txt` | C-15 | Servidor con `SQL_ECHO=true`; `GET /ordenes/3` (2 ítems) y `GET /ordenes/4` (4 ítems): 6 consultas en las dos |
| `C-12_aviso_segundo_plano.txt` | C-11, C-12 | Terminar la orden 2 sin stock (409, sin aviso), reponer y terminar: COMMIT → 200 → el aviso medio segundo después |

Para repetir C-15: levantar el servidor con `SQL_ECHO=true`, iniciar sesión como
`admin@example.com`, crear una orden con 2 ítems y otra con 4 (`POST /ordenes`) y pedir el
detalle de cada una. Entre las dos sólo cambian los parámetros del `IN` de repuestos.
