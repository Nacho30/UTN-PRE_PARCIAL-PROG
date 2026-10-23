"""Importa todos los modelos de tabla para que queden registrados en `SQLModel.metadata`.

Lo usan `main.py`, `seed.py` y `migrations/env.py`: las relaciones se declaran con nombres
de clase entre comillas y SQLAlchemy las resuelve cuando todas las clases existen.
"""

from app.modules.clientes.models import Cliente, Vehiculo
from app.modules.ordenes.models import EstadoOrden, HistorialEstadoOrden, ItemOrden, OrdenTrabajo
from app.modules.repuestos.models import HistorialPrecio, MovimientoStock, Repuesto
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, IntentoAcceso, Usuario

__all__ = [
    "AsignacionRol",
    "Cliente",
    "EstadoOrden",
    "EventoSeguridad",
    "HistorialEstadoOrden",
    "HistorialPrecio",
    "IntentoAcceso",
    "ItemOrden",
    "MovimientoStock",
    "OrdenTrabajo",
    "Repuesto",
    "Usuario",
    "Vehiculo",
]
