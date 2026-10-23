"""Repuestos, movimientos de stock e historial de precios.

`movimiento_stock` e `historial_precio_repuesto` son de sólo agregado: el disparador de la
migración 0002 rechaza cualquier UPDATE o DELETE sobre ellas (RN-15).
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

from app.core.tipos import columna_dinero, columna_momento
from app.modules.usuarios.models import SIN_CARGA_PEREZOSA

if TYPE_CHECKING:
    from app.modules.ordenes.models import ItemOrden


class Repuesto(SQLModel, table=True):
    __tablename__ = "repuesto"
    __table_args__ = (
        CheckConstraint("precio > 0", name="precio_positivo"),
        CheckConstraint("stock >= 0", name="stock_no_negativo"),
        Index("ux_repuesto_codigo_vigente", "codigo", unique=True, postgresql_where=text("borrado_en IS NULL")),
    )

    id: int | None = Field(default=None, primary_key=True)
    codigo: str = Field(max_length=30)
    descripcion: str = Field(max_length=200)
    precio: Decimal = columna_dinero(10)
    # RN-14: sólo cambia a través de movimientos (el punto único de stock llega en el ejercicio 6).
    stock: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
    borrado_en: datetime | None = columna_momento(nullable=True)

    movimientos: list["MovimientoStock"] = Relationship(back_populates="repuesto", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    historial_precios: list["HistorialPrecio"] = Relationship(back_populates="repuesto", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    items_orden: list["ItemOrden"] = Relationship(back_populates="repuesto", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)


class MovimientoStock(SQLModel, table=True):
    __tablename__ = "movimiento_stock"
    __table_args__ = (CheckConstraint("cantidad <> 0", name="cantidad_distinta_de_cero"),)

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    orden_id: int | None = Field(default=None, foreign_key="orden_trabajo.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    cantidad: int  # positiva = entrada, negativa = salida
    motivo: str = Field(max_length=200)
    cuando: datetime = columna_momento(por_defecto_ahora=True)

    repuesto: Repuesto = Relationship(back_populates="movimientos", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)


class HistorialPrecio(SQLModel, table=True):
    __tablename__ = "historial_precio_repuesto"
    __table_args__ = (
        CheckConstraint("precio_nuevo > 0", name="precio_nuevo_positivo"),
        CheckConstraint("precio_nuevo <> precio_anterior", name="precio_cambia"),
    )

    id: int | None = Field(default=None, primary_key=True)
    repuesto_id: int = Field(foreign_key="repuesto.id", index=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    precio_anterior: Decimal = columna_dinero(10)
    precio_nuevo: Decimal = columna_dinero(10)
    cuando: datetime = columna_momento(por_defecto_ahora=True)

    repuesto: Repuesto = Relationship(back_populates="historial_precios", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
