# Contexto y actores

## Problema

Un taller mecánico necesita una API para su trabajo diario. La **recepción** da de alta a los
clientes y a sus vehículos, y abre una **orden de trabajo** por cada ingreso, con la falla que
describe el cliente y los repuestos que se van a usar. Un **mecánico** toma la orden, la repara
y la da por terminada: en ese momento se descuenta el stock de cada repuesto usado. El
**administrador** mantiene el catálogo de repuestos, repone el stock y administra al personal y
sus roles. Los **clientes** se registran solos y consultan el estado de sus vehículos.

## Objetivos del proyecto (lo que el TP evalúa)

1. API asincrónica en capas **Router → Service → UoW → Repository → Model**, donde cada capa
   sabe lo suyo y nada más.
2. Un modelo con asociación, composición, uno a uno y catálogo, traducido a un esquema
   relacional versionado con Alembic, con una migración escrita a mano.
3. Autenticación con bcrypt y token en cookie `HttpOnly`, sin frenar el servidor y sin revelar
   qué cuentas existen.
4. Autorización consultando los roles **en la base** en cada petición, con vigencia, y
   distinguiendo siempre 401 de 403.
5. Escrituras de una operación de negocio agrupadas en una sola transacción.
6. Delegar en la base lo que la base puede garantizar: unicidad, claves foráneas,
   comprobaciones y sólo agregado.

## Actores

| Actor | Rol en la base | Qué hace |
|---|---|---|
| Visitante | — | Se registra como cliente, inicia sesión, consulta la salud del servicio |
| Cliente | `CLIENTE` | Ve sus vehículos y las órdenes de sus vehículos; cancela las suyas si están pendientes |
| Recepción | `RECEPCION` | Alta de clientes y vehículos, baja de vehículos, alta y cancelación de órdenes |
| Mecánico | `MECANICO` | Inicia órdenes (queda asignado) y termina las suyas |
| Administrador | `ADMIN` | Repuestos, stock, precios, personal, roles, historial de seguridad; también termina órdenes |
| Sistema | — (texto `SISTEMA`) | Actor de la carga inicial en el historial de seguridad |

Un usuario puede tener varios roles a la vez. Los roles tienen vigencia (`desde`, `vence_en`,
`revocada_en`).

## Por qué este dominio (de la consigna)

| Lo que pide el dominio | Concepto | Capítulo |
|---|---|---|
| La orden nace con sus ítems; un ítem no existe sin su orden | Composición | 4 |
| Un cliente puede tener o no un usuario, y a lo sumo uno | Uno a uno opcional | 4 |
| Un vehículo vendido se da de baja y el comprador lo registra con la misma patente | Borrado lógico + índice único parcial | 4 y 6 |
| Cuatro roles con vigencia, asignados y revocados por el admin | Autorización en la base | 5 |
| El registro crea usuario, rol y ficha de cliente | Tres escrituras en una transacción | 6 |
| Terminar una orden descuenta el stock | Cuatro clases de escritura en una transacción | 6 |
| El límite de intentos de login cuenta una tabla | El intento sobrevive al rollback | 5 y 6 |
| Los estados de una orden son una lista fija | Catálogo con clave foránea, cargado por `seed.py` | 4 |
| Historial de estados, movimientos y precios no se corrigen | Sólo agregado impuesto por la base | 6 |

## Alcance

**Adentro:** todo lo anterior, los endpoints de referencia, los datos iniciales y los casos
C-01 a C-19.

**Afuera (lo dice la consigna):**
- **Concurrencia (capítulo 7).** Dos terminaciones simultáneas pueden leer el mismo stock y
  pisarse (actualización perdida). El bloqueo que lo evita es tema de la próxima unidad.
- **Colas de tareas (capítulo 8).** El aviso al cliente corre con `BackgroundTasks` en el mismo
  proceso: si el proceso se reinicia, se pierde y no hay reintento. Se acepta porque es simulado.
- **Rol de base sin permisos** sobre las tablas de sólo agregado (sección 6.9): no se pide; el
  TP usa un solo rol de base y alcanza con el disparador.

## Condiciones de corrección

Un proyecto que no levanta, que no crea su esquema con `alembic upgrade head` sobre una base
vacía o que contiene credenciales reales en el repositorio **no se corrige** hasta que se
subsane.
