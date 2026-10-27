"""Contratos de entrada y salida del módulo de clientes y vehículos."""

from datetime import datetime
from pydantic import field_validator
from sqlmodel import Field, SQLModel

from app.core.tipos import EntradaEstricta, normalizar_patente, texto


class ClienteCrear(EntradaEstricta):
    nombre: texto(120)
    documento: texto(20)
    telefono: texto(30) | None = None


class VehiculoCrear(EntradaEstricta):
    patente: texto(10)
    marca: texto(60)
    modelo: texto(60)
    anio: int = Field(ge=1950, le=2100)

    @field_validator("patente", mode="after")
    @classmethod
    def normalizar_patente_val(cls, v: str) -> str:
        return normalizar_patente(v)


class VehiculoOut(SQLModel):
    id: int
    cliente_id: int
    patente: str
    marca: str
    modelo: str
    anio: int
    borrado_en: datetime | None = None


class ClienteOut(SQLModel):
    id: int
    usuario_id: int | None = None
    nombre: str
    documento: str
    telefono: str | None = None


class ClienteDetalleOut(ClienteOut):
    vehiculos: list[VehiculoOut] = []
