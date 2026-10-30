"""Contratos de entrada y salida del módulo de usuarios, autenticación y autorización."""

from datetime import datetime

from pydantic import AwareDatetime, field_validator
from sqlmodel import Field, SQLModel

from app.core.tipos import (
    Documento,
    EmailNormalizado,
    EntradaEstricta,
    PasswordBcrypt,
    Telefono,
    TextoCorto,
    ahora,
)
from app.modules.usuarios.models import ROLES_PERSONAL, Rol


class CredencialesCrear(EntradaEstricta):
    email: EmailNormalizado
    nombre: TextoCorto
    password: PasswordBcrypt


class RegistroIn(CredencialesCrear):
    documento: Documento
    telefono: Telefono | None = None


class LoginIn(EntradaEstricta):
    email: EmailNormalizado
    password: PasswordBcrypt


class LoginOut(SQLModel):
    mensaje: str = "Sesión iniciada"
    debe_cambiar_password: bool = False
    expira_en_segundos: int = 1800


class LogoutOut(SQLModel):
    mensaje: str = "Sesión cerrada"


class UsuarioOut(SQLModel):
    id: int
    email: str
    nombre: str
    roles: list[str]
    activo: bool
    debe_cambiar_password: bool = False


class UsuarioActualOut(UsuarioOut):
    roles_vigentes: list[str]
    roles_token: list[str]
    debe_cambiar_password: bool = False


YoOut = UsuarioActualOut


class PersonalCrear(CredencialesCrear):
    roles: list[Rol] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def validar_personal(cls, roles: list[Rol]) -> list[Rol]:
        if len(set(roles)) != len(roles) or any(
            rol not in ROLES_PERSONAL for rol in roles
        ):
            raise ValueError(
                "Los roles de personal deben ser distintos y no pueden incluir CLIENTE"
            )
        return roles


class AsignacionCrear(EntradaEstricta):
    rol: Rol
    vence_en: AwareDatetime | None = None

    @field_validator("vence_en")
    @classmethod
    def validar_vencimiento(cls, vence_en: datetime | None) -> datetime | None:
        if vence_en is not None and vence_en <= ahora():
            raise ValueError("El vencimiento debe ser futuro y tener zona horaria")
        return vence_en


class AsignacionOut(SQLModel):
    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None
    revocada_en: datetime | None
    otorgada_por: int | None
    vigente: bool


class CambiarPasswordIn(EntradaEstricta):
    password_actual: PasswordBcrypt
    password_nueva: PasswordBcrypt


class EventoOut(SQLModel):
    id: int
    cuando: datetime
    actor: str
    accion: str
