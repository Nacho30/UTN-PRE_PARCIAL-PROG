from pydantic import EmailStr
from app.core.tipos import EntradaEstricta, PasswordBcrypt, texto


class RegistroIn(EntradaEstricta):
    email: EmailStr
    nombre: texto(120)
    password: PasswordBcrypt


class LoginIn(EntradaEstricta):
    email: EmailStr
    password: PasswordBcrypt


class UsuarioOut(EntradaEstricta):
    id: int
    email: str
    nombre: str
    roles: list[str]
    activo: bool
