"""Usuarios, roles, intentos de acceso y eventos de seguridad.

`usuario` no tiene una columna `rol`: los roles de una persona son las filas vigentes de
`asignacion_rol` (no revocadas y sin vencer). Revocar escribe `revocada_en` y la fila no se
borra nunca: así queda el historial de quién tuvo qué rol y hasta cuándo (sección 5.9).
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Index, text
from sqlmodel import Field, Relationship, SQLModel

from app.core.tipos import columna_momento

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente


class Rol(StrEnum):
    ADMIN = "ADMIN"
    RECEPCION = "RECEPCION"
    MECANICO = "MECANICO"
    CLIENTE = "CLIENTE"


ROLES_PERSONAL = (Rol.ADMIN, Rol.RECEPCION, Rol.MECANICO)

# Toda relación se precarga en el repositorio. Con raise_on_sql, leer una relación que no se
# precargó falla en lugar de disparar una consulta escondida (sección 3.8).
SIN_CARGA_PEREZOSA = {"lazy": "raise_on_sql"}


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=254, unique=True)
    nombre: str = Field(max_length=120)
    password_hash: str = Field(max_length=100)
    activo: bool = Field(default=True, sa_column_kwargs={"server_default": text("true")})
    debe_cambiar_password: bool = Field(default=False, sa_column_kwargs={"server_default": text("false")})
    password_cambiada_en: datetime | None = columna_momento(nullable=True)

    asignaciones: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={**SIN_CARGA_PEREZOSA, "foreign_keys": "[AsignacionRol.usuario_id]"},
    )
    # Uno a uno opcional: devuelve un objeto (o None), no una lista.
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={**SIN_CARGA_PEREZOSA, "uselist": False},
    )


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint("rol IN ('ADMIN', 'RECEPCION', 'MECANICO', 'CLIENTE')", name="rol_valido"),
        # RN-03: a lo sumo una asignación abierta por rol. Las revocadas no cuentan, así que
        # el historial puede tener muchas filas del mismo rol.
        Index(
            "ux_asignacion_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    rol: str = Field(max_length=20)
    desde: datetime = columna_momento(por_defecto_ahora=True)
    vence_en: datetime | None = columna_momento(nullable=True)
    revocada_en: datetime | None = columna_momento(nullable=True)
    otorgada_por: int | None = Field(default=None, foreign_key="usuario.id", index=True)

    usuario: Usuario = Relationship(
        back_populates="asignaciones",
        sa_relationship_kwargs={**SIN_CARGA_PEREZOSA, "foreign_keys": "[AsignacionRol.usuario_id]"},
    )


class IntentoAcceso(SQLModel, table=True):
    """Cada intento de login. Se escribe en su propia transacción (ver AccesoUnitOfWork)."""

    __tablename__ = "intento_acceso"
    __table_args__ = (Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),)

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = columna_momento(por_defecto_ahora=True)
    email: str = Field(max_length=254)
    ip: str = Field(max_length=45)
    exito: bool


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = columna_momento(por_defecto_ahora=True)
    # Texto y no clave foránea: el actor puede ser «SISTEMA», que no es un usuario (sección 5.8).
    actor: str = Field(max_length=254)
    accion: str = Field(max_length=500)
