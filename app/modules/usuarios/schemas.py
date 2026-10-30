"""Contratos de entrada y salida del módulo de usuarios y autenticación."""

from sqlmodel import SQLModel

from app.core.tipos import (
    Documento,
    EmailNormalizado,
    EntradaEstricta,
    PasswordBcrypt,
    Telefono,
    TextoCorto,
)


class RegistroIn(EntradaEstricta):
    email: EmailNormalizado
    nombre: TextoCorto
    password: PasswordBcrypt
    documento: Documento
    telefono: Telefono | None = None


class LoginIn(EntradaEstricta):
    email: EmailNormalizado
    password: PasswordBcrypt


class LoginOut(SQLModel):
    mensaje: str = "Sesión iniciada"
    debe_cambiar_password: bool
    expira_en_segundos: int


class LogoutOut(SQLModel):
    mensaje: str = "Sesión cerrada"


class UsuarioOut(SQLModel):
    id: int
    email: str
    nombre: str
    roles: list[str]
    activo: bool
    debe_cambiar_password: bool = False


class YoOut(UsuarioOut):
    roles_vigentes: list[str]
    roles_token: list[str]
