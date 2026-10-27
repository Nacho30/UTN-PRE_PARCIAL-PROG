# Evidencias

Capturas que pide el formato de entrega:

| Archivo | Caso | Cómo se obtiene |
|---|---|---|
| `c14_solo_agregado.png` | C-14 | `psql -h localhost -U taller -d taller -f test/solo_agregado.sql` después de `python seed.py` |
| `c15_consultas_detalle.png` | C-15 | Servidor con `SQL_ECHO=true`; `GET /ordenes/3` (2 ítems) y `GET /ordenes/4` (4 ítems) |
