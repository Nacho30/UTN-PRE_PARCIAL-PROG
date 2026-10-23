"""Órdenes de trabajo, sus ítems, su historial y el catálogo de estados.

El catálogo `estado_orden` reemplaza a un CHECK con la lista adentro: la base sigue
rechazando un estado que no existe —por la clave foránea— y cada estado lleva datos propios,
como `es_final`, que decide qué es una orden abierta (RN-16). La clave primaria es el código
y no un id, para que `orden_trabajo.estado` se lea igual en psql que en la API.

El enum `EstadoOrdenCodigo` es el contrato de la API (un estado que no declara da 422) y el
vocabulario con que el servicio decide las transiciones. Enum y catálogo tienen que
coincidir: agregar un estado obliga a tocar los dos y el servicio.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.tipos import columna_dinero, columna_momento
from app.modules.clientes.models import Vehiculo
from app.modules.repuestos.models import Repuesto
from app.modules.usuarios.models import SIN_CARGA_PEREZOSA


class EstadoOrdenCodigo(StrEnum):
    PENDIENTE = "PENDIENTE"
    EN_REPARACION = "EN_REPARACION"
    TERMINADA = "TERMINADA"
    CANCELADA = "CANCELADA"


class EstadoOrden(SQLModel, table=True):
    """Catálogo. La migración crea la tabla vacía; sus filas las carga seed.py."""

    __tablename__ = "estado_orden"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=200)
    posicion: int = Field(unique=True)
    es_final: bool = False


class OrdenTrabajo(SQLModel, table=True):
    __tablename__ = "orden_trabajo"
    __table_args__ = (CheckConstraint("total >= 0", name="total_no_negativo"),)

    id: int | None = Field(default=None, primary_key=True)
    vehiculo_id: int = Field(foreign_key="vehiculo.id", index=True)
    mecanico_id: int | None = Field(default=None, foreign_key="usuario.id", index=True)
    estado: str = Field(foreign_key="estado_orden.codigo", index=True, max_length=20)
    falla: str = Field(max_length=500)
    creada_en: datetime = columna_momento(por_defecto_ahora=True)
    total: Decimal = columna_dinero(12)

    vehiculo: Vehiculo = Relationship(back_populates="ordenes", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    # Composición: el ítem nace con la orden y no existe sin ella.
    items: list["ItemOrden"] = Relationship(
        back_populates="orden",
        sa_relationship_kwargs={**SIN_CARGA_PEREZOSA, "cascade": "all, delete-orphan", "order_by": "ItemOrden.id"},
    )
    # Composición de sólo agregado: se guarda con la orden, nunca se borra.
    historial: list["HistorialEstadoOrden"] = Relationship(
        back_populates="orden",
        sa_relationship_kwargs={**SIN_CARGA_PEREZOSA, "order_by": "HistorialEstadoOrden.id"},
    )


class ItemOrden(SQLModel, table=True):
    __tablename__ = "item_orden"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint("precio_unitario > 0", name="precio_unitario_positivo"),
        UniqueConstraint("orden_id", "repuesto_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    cantidad: int
    # Copiado del repuesto al crear la orden (RN-10): un cambio de precio posterior no la toca.
    precio_unitario: Decimal = columna_dinero(10)

    orden: OrdenTrabajo = Relationship(back_populates="items", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    repuesto: Repuesto = Relationship(back_populates="items_orden", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)


class HistorialEstadoOrden(SQLModel, table=True):
    __tablename__ = "historial_estado_orden"

    id: int | None = Field(default=None, primary_key=True)
    orden_id: int = Field(foreign_key="orden_trabajo.id", index=True)
    desde_estado: str | None = Field(default=None, foreign_key="estado_orden.codigo", index=True, max_length=20)
    hasta_estado: str = Field(foreign_key="estado_orden.codigo", index=True, max_length=20)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cuando: datetime = columna_momento(por_defecto_ahora=True)

    orden: Optional[OrdenTrabajo] = Relationship(back_populates="historial", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
