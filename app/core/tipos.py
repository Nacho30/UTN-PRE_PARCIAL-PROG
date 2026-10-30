"""Tipos comunes de columnas y contratos de la API.

La `naming_convention` se fija acá, antes de que se defina cualquier modelo: así cada
restricción tiene un nombre predecible (`uq_usuario_email`, `ck_repuesto_precio_positivo`,
...) que Alembic escribe igual en la migración y que más adelante sirve para traducir un
IntegrityError a un 409 con mensaje propio.
"""

from datetime import UTC, datetime
from decimal import Decimal
import re
from typing import Annotated, Any

from fastapi import Path
from pydantic import AfterValidator, ConfigDict, EmailStr
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


# --- Contratos y tipos acotados para endpoints (Ejercicio 3) -----------------


class EntradaEstricta(SQLModel):
    """Base de esquemas de entrada: rechaza campos no declarados y limpia espacios."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


IdEntero = Annotated[int, Field(ge=1, le=2_147_483_647)]
IdPath = Annotated[int, Path(ge=1, le=2_147_483_647)]
Dinero = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


def _validar_sin_caracter_nulo(v: str) -> str:
    if "\x00" in v:
        raise ValueError("El texto no puede contener caracteres nulos")
    return v


def texto(max_len: int, *, min_len: int = 1) -> Any:
    """Tipo de cadena acotada que rechaza vacíos tras strip y caracteres nulos."""
    return Annotated[
        str,
        Field(min_length=min_len, max_length=max_len),
        AfterValidator(_validar_sin_caracter_nulo),
    ]


def _validar_max_72_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar los 72 bytes en UTF-8")
    return v


PasswordTexto = Annotated[
    str,
    Field(min_length=8),
    AfterValidator(_validar_max_72_bytes),
]


PasswordBcrypt = Annotated[
    str,
    Field(min_length=8),
    AfterValidator(_validar_max_72_bytes),
]


def normalizar_patente(patente: str) -> str:
    """Mayúsculas sin espacios ni guiones (D-06)."""
    return re.sub(r"[\s\-]", "", patente).upper()


def normalizar_codigo(codigo: str) -> str:
    """Mayúsculas sin espacios ni guiones (D-06)."""
    return re.sub(r"[\s\-]", "", codigo).upper()


def normalizar_email(email: str) -> str:
    """Minúsculas sin espacios alrededor (D-06)."""
    return email.strip().lower()


EmailNormalizado = Annotated[
    EmailStr,
    AfterValidator(normalizar_email),
    Field(max_length=254),
]
TextoCorto = texto(120)
Documento = texto(20)
Telefono = texto(30)
