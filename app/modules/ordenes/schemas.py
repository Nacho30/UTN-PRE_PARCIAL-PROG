"""Contratos de entrada y salida del módulo de órdenes de trabajo."""

from datetime import datetime
from decimal import Decimal
from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.core.tipos import EntradaEstricta, IdEntero, texto


class ItemOrdenCrear(EntradaEstricta):
    repuesto_id: IdEntero
    cantidad: int = Field(gt=0, le=2_147_483_647)


class OrdenCrear(EntradaEstricta):
    vehiculo_id: IdEntero
    falla: texto(500)
    items: list[ItemOrdenCrear] = Field(min_length=1)

    @field_validator("items", mode="after")
    @classmethod
    def validar_sin_repuestos_repetidos(cls, items: list[ItemOrdenCrear]) -> list[ItemOrdenCrear]:
        ids = [it.repuesto_id for it in items]
        if len(ids) != len(set(ids)):
            raise ValueError("La orden tiene repuestos repetidos")
        return items


class ItemOrdenOut(SQLModel):
    repuesto_id: int
    codigo: str
    descripcion: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class HistorialEstadoOut(SQLModel):
    desde_estado: str | None = None
    hasta_estado: str
    usuario_id: int
    cuando: datetime


class OrdenClienteResumen(SQLModel):
    id: int
    nombre: str
    documento: str


class OrdenResumenOut(SQLModel):
    id: int
    estado: str
    patente: str
    total: Decimal
    creada_en: datetime
    mecanico_id: int | None = None


class OrdenDetalleOut(SQLModel):
    """Detalle de orden según formato de la página 18 de la consigna."""

    id: int
    estado: str
    patente: str
    total: Decimal
    creada_en: datetime
    mecanico_id: int | None = None
    falla: str
    cliente: OrdenClienteResumen
    items: list[ItemOrdenOut]
    historial: list[HistorialEstadoOut]


class EstadoOrdenOut(SQLModel):
    codigo: str
    descripcion: str
    posicion: int
    es_final: bool
