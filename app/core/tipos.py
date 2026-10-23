"""Tipos comunes de columnas.

La `naming_convention` se fija acá, antes de que se defina cualquier modelo: así cada
restricción tiene un nombre predecible (`uq_usuario_email`, `ck_repuesto_precio_positivo`,
...) que Alembic escribe igual en la migración y que más adelante sirve para traducir un
IntegrityError a un 409 con mensaje propio.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Numeric, func
from sqlmodel import Field, SQLModel

SQLModel.metadata.naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def ahora() -> datetime:
    return datetime.now(UTC)


def columna_momento(*, nullable: bool = False, por_defecto_ahora: bool = False) -> Any:
    """Columna `timestamptz`. Todas las fechas del sistema llevan zona.

    Con `por_defecto_ahora`, el valor se pone en Python (así está disponible sin releer la
    fila) y también en la base, para las filas que se insertan desde psql.
    """
    if por_defecto_ahora:
        return Field(
            default_factory=ahora,
            sa_column=Column(DateTime(timezone=True), nullable=nullable, server_default=func.now()),
        )
    return Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=nullable))


def columna_dinero(precision: int = 10, *, nullable: bool = False) -> Any:
    """Columna `NUMERIC(precision, 2)`. El dinero nunca es float (sección 2.7)."""
    return Field(sa_column=Column(Numeric(precision, 2), nullable=nullable))
