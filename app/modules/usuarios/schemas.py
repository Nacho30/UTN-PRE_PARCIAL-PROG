"""Contratos de entrada y salida del módulo de usuarios.

Ningún esquema de salida expone `password_hash`.
Las entradas heredan de `EntradaEstricta` (`extra="forbid"`).
"""

from datetime import datetime
from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel

from app.core.tipos import EntradaEstricta, PasswordTexto, normalizar_email, texto
from app.modules.usuarios.models import Rol


class RegistroIn(EntradaEstricta):
    nombre: texto(120)
    email: EmailStr
    password: PasswordTexto
    documento: texto(20)
    telefono: texto(30) | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_correo(cls, v: EmailStr) -> str:
        return normalizar_email(str(v))


class LoginIn(EntradaEstricta):
    email: EmailStr
    password: PasswordTexto

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_correo(cls, v: EmailStr) -> str:
        return normalizar_email(str(v))


class LoginOut(SQLModel):
    mensaje: str = "Sesión iniciada"
    debe_cambiar_password: bool = False
    expira_en_segundos: int = 1800


class CambiarPasswordIn(EntradaEstricta):
    password_actual: PasswordTexto
    password_nueva: PasswordTexto


class UsuarioCrear(EntradaEstricta):
    nombre: texto(120)
    email: EmailStr
    password: PasswordTexto

    @field_validator("email", mode="after")
    @classmethod
    def normalizar_correo(cls, v: EmailStr) -> str:
        return normalizar_email(str(v))


class UsuarioOut(SQLModel):
    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    password_cambiada_en: datetime | None = None


class YoOut(SQLModel):
    id: int
    email: str
    nombre: str
    roles: list[str] = []


class AsignarRolIn(EntradaEstricta):
    rol: Rol
    vence_en: datetime | None = None


class AsignacionRolOut(SQLModel):
    id: int
    usuario_id: int
    rol: str
    desde: datetime
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    otorgada_por: int | None = None


class EventoSeguridadOut(SQLModel):
    id: int
    cuando: datetime
    actor: str
    accion: str
