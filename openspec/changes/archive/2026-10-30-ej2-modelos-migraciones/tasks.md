# Tareas · Ejercicio 2

## 1. Modelos
- [x] 1.1 `naming_convention` en la metadata para nombres de restricciones predecibles
- [x] 1.2 Tipos comunes: `timestamptz`, `NUMERIC(10,2)`, `NUMERIC(12,2)`
- [x] 1.3 `usuarios`: Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
- [x] 1.4 `clientes`: Cliente (uno a uno opcional con Usuario), Vehiculo (borrado lógico)
- [x] 1.5 `repuestos`: Repuesto (borrado lógico), MovimientoStock, HistorialPrecio
- [x] 1.6 `ordenes`: EstadoOrden (catálogo), OrdenTrabajo, ItemOrden, HistorialEstadoOrden
- [x] 1.7 CHECKs, UNIQUE e índices únicos parciales de la tabla de la consigna
- [x] 1.8 Relaciones en ambos extremos, `Usuario.cliente` con `uselist=False`
- [x] 1.9 Índice en cada clave foránea

## 2. Migraciones
- [x] 2.1 `alembic init -t async migrations`; `env.py` toma la URL de `Settings`
- [x] 2.2 `alembic.ini` sin URL ni credenciales
- [x] 2.3 `0001_esquema_inicial` con `--autogenerate`, revisada y comentada
- [x] 2.4 `0002_solo_agregado` escrita a mano, con su `downgrade`
- [ ] 2.5 `upgrade head` → `downgrade base` → `upgrade head` sin errores, y `alembic check` limpio
      (el SQL equivalente ya se probó en PostgreSQL 16; falta correrlo con Alembic en la máquina)
