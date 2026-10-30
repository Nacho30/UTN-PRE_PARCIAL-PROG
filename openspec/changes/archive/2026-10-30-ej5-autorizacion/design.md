# Diseño · Autorización

## Context
La motivación está en proposal.md. El CRUD ya existe, pero dependencies.py está vacío y sus
rutas usan actores fijos. Se conservan los modelos y la arquitectura Router → Service → UoW
→ Repository. No se modifica el esquema.

## Goals / Non-Goals
Se implementan las reglas de autorización con las asignaciones vigentes en cada petición,
conservando las respuestas existentes y agregando los campos informativos del token.
El punto único de stock y la refactorización de transacciones corresponden al ejercicio 6.

## Decisions
- Una dependencia devuelve el usuario autenticado y sus roles actuales y del token. Lee sólo
  la cookie, valida el JWT, consulta usuario y asignaciones en lectura_corta y compara iat y
  password_cambiada_en como microsegundos enteros. Se descarta usar los roles del JWT para
  decidir permisos porque impediría revocar sesiones abiertas.
- La consulta de roles filtra revocada_en nula, desde menor o igual al instante de consulta y
  vence_en nula o posterior. Se reutiliza en login, /auth/yo y controles de permisos.
- main.py monta exigir_password_al_dia una sola vez en el grupo protegido. /auth y /health
  quedan abiertos; cada endpoint autenticado de /auth usa su dependencia de identidad.
- Los routers aplican los roles de personal del discovery. Detalle, cancelación y terminación
  verifican en el servicio existencia, permiso y estado en ese orden. Los listados propios
  filtran por cliente.usuario_id y no requieren el rol CLIENTE.
- El servicio de usuarios recibe el UoW desde una dependencia. Las escrituras de personal,
  roles y contraseña agregan su evento de seguridad dentro de la misma transacción.
- Revocar un rol conserva su fila. Reasignar un rol vencido cierra la asignación abierta antes
  de insertar la nueva. La protección ADMIN verifica identidad y administradores activos con
  asignación vigente dentro del servicio. Se mantiene el alcance sin concurrencia del TP.
- El cambio de contraseña verifica la actual y calcula bcrypt antes de abrir la transacción;
  actualiza hash, instante y bandera juntos. Luego emite la cookie nueva. No se trunca iat.

## Risks / Trade-offs
- Fechas con precisión de microsegundos → conversión decimal del iat y aritmética entera UTC,
  pruebas del límite y del cambio inmediato.
- Ampliación de permisos sobre CRUD existente → pruebas HTTP con distintos usuarios y
  revisión de la matriz de endpoints; se eliminan los actores fijos al conectarlos.
- Pruebas con seed destructivo → sólo base PostgreSQL desechable explícitamente validada.

## Migration Plan
No hay migraciones. Se despliega el código junto; para revertir se revierte el commit del
change. Las asignaciones revocadas y eventos conservan el historial en las tablas existentes.
