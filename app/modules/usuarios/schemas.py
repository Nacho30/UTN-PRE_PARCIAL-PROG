from datetime import datetime

from pydantic import AwareDatetime, EmailStr, field_validator
from sqlmodel import Field, SQLModel

from app.core.tipos import EntradaEstricta, PasswordBcrypt, ahora, texto
from app.modules.usuarios.models import ROLES_PERSONAL, Rol


class CredencialesCrear(EntradaEstricta):
    email: EmailStr
    nombre: texto(120)
    password: PasswordBcrypt


class RegistroIn(CredencialesCrear):
    documento: texto(20)
    telefono: texto(30) | None = None


class LoginIn(EntradaEstricta):
    email: EmailStr
    password: PasswordBcrypt


class UsuarioOut(EntradaEstricta):
    id: int
    email: str
    nombre: str
    roles: list[str]
    activo: bool


class UsuarioActualOut(UsuarioOut):
    roles_vigentes: list[str]
    roles_token: list[str]
    debe_cambiar_password: bool


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
