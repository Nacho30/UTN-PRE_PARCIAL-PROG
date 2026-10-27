"""Contratos de entrada y salida del módulo de repuestos."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from app.core.tipos import Dinero, EntradaEstricta, normalizar_codigo, texto


class RepuestoCrear(EntradaEstricta):
    codigo: texto(30)
    descripcion: texto(200)
    precio: Dinero
    stock_inicial: int = Field(default=0, ge=0, le=2_147_483_647)

    @field_validator("codigo", mode="after")
    @classmethod
    def normalizar_codigo_val(cls, v: str) -> str:
        return normalizar_codigo(v)


class RepuestoPatch(EntradaEstricta):
    """PATCH parcial: sólo acepta descripcion y precio.

    Rechaza stock con 422 (extra='forbid') y rechaza null explícito en los campos enviados.
    """

    descripcion: texto(200) | None = None
    precio: Dinero | None = None

    @model_validator(mode="before")
    @classmethod
    def rechazar_nulos_explicitos(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for campo, valor in data.items():
                if valor is None:
                    raise ValueError(f"El campo '{campo}' no puede ser nulo")
        return data


class ReponerStockIn(EntradaEstricta):
    cantidad: int = Field(gt=0, le=2_147_483_647)
    motivo: texto(200)


class RepuestoOut(SQLModel):
    id: int
    codigo: str
    descripcion: str
    precio: Decimal
    stock: int
    borrado_en: datetime | None = None


class MovimientoStockOut(SQLModel):
    id: int
    repuesto_id: int
    orden_id: int | None = None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime


class HistorialPrecioOut(SQLModel):
    id: int
    repuesto_id: int
    usuario_id: int
    precio_anterior: Decimal
    precio_nuevo: Decimal
    cuando: datetime
