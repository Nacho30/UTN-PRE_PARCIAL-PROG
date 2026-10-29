"""Hash de contraseñas con bcrypt.

En el ejercicio 1 lo usa el lifespan para calcular, una sola vez, el hash ficticio del login.
La emisión y verificación del token se agregan en el ejercicio 4.

bcrypt es lento a propósito (~300 ms con costo 12). Si corriera en el bucle de eventos,
mientras calcula un hash ningún otro cliente sería atendido (sección 5.6). Por eso toda
llamada va a `asyncio.to_thread`, y un semáforo limita cuántas corren a la vez.
"""

import asyncio
from datetime import UTC, datetime
import bcrypt
import jwt

from app.core.config import Settings, get_settings

BCRYPT_MAX_BYTES = 72

_semaforo: asyncio.Semaphore | None = None


def _get_semaforo() -> asyncio.Semaphore:
    # Se crea en el primer uso, ya dentro del bucle de eventos, no al importar.
    global _semaforo
    if _semaforo is None:
        _semaforo = asyncio.Semaphore(get_settings().BCRYPT_CONCURRENCIA)
    return _semaforo


def _hash_sync(password: str, rounds: int) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def _verificar_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


async def hash_password(password: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    async with _get_semaforo():
        return await asyncio.to_thread(_hash_sync, password, settings.BCRYPT_ROUNDS)


async def verificar_password(password: str, password_hash: str) -> bool:
    async with _get_semaforo():
        return await asyncio.to_thread(_verificar_sync, password, password_hash)


def crear_token(sub: str, roles: list[str], settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    ahora = datetime.now(UTC)
    payload = {
        "sub": sub,
        "iat": ahora.timestamp(),  # float con fracción de segundo
        "exp": ahora.timestamp() + settings.jwt_expira_segundos,
        "roles": roles,
    }
    return jwt.encode(payload, settings.JWT_SECRET.get_secret_value(), algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token: str, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    return jwt.decode(
        token,
        settings.JWT_SECRET.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )

