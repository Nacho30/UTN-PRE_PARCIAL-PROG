"""Clientes y vehículos.

- Un cliente puede tener o no un usuario, y a lo sumo uno: `cliente.usuario_id` UNIQUE y
  nulo permitido (uno a uno opcional).
- Un vehículo vendido se da de baja (borrado lógico) y sus órdenes viejas siguen. La patente
  es única sólo entre los vigentes: con un UNIQUE común, el comprador no podría registrarlo
  y la base respondería «ya existe» de un vehículo que la API no muestra (sección 4.9).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

from app.core.tipos import columna_momento
from app.modules.usuarios.models import SIN_CARGA_PEREZOSA, Usuario

if TYPE_CHECKING:
    from app.modules.ordenes.models import OrdenTrabajo


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    # UNIQUE: PostgreSQL crea el índice de la restricción, que sirve para la clave foránea.
    usuario_id: int | None = Field(default=None, foreign_key="usuario.id", unique=True)
    nombre: str = Field(max_length=120)
    documento: str = Field(max_length=20, unique=True)
    telefono: str | None = Field(default=None, max_length=30)

    usuario: Optional[Usuario] = Relationship(back_populates="cliente", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    vehiculos: list["Vehiculo"] = Relationship(back_populates="cliente", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)


class Vehiculo(SQLModel, table=True):
    __tablename__ = "vehiculo"
    __table_args__ = (
        CheckConstraint("anio BETWEEN 1950 AND 2100", name="anio_valido"),
        Index("ux_vehiculo_patente_vigente", "patente", unique=True, postgresql_where=text("borrado_en IS NULL")),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    patente: str = Field(max_length=10)
    marca: str = Field(max_length=60)
    modelo: str = Field(max_length=60)
    anio: int
    borrado_en: datetime | None = columna_momento(nullable=True)

    cliente: Cliente = Relationship(back_populates="vehiculos", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
    ordenes: list["OrdenTrabajo"] = Relationship(back_populates="vehiculo", sa_relationship_kwargs=SIN_CARGA_PEREZOSA)
