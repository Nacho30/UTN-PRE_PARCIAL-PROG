"""Configuración leída del entorno (o de un `.env` que no se versiona).

`POSTGRES_PASSWORD` y `JWT_SECRET` no tienen valor por defecto: si faltan, `Settings()`
falla y la aplicación no arranca. La clave de firma es el secreto más importante del
sistema —quien la tenga fabrica un token válido para cualquier usuario (sección 5.12)— y
una clave inventada al arrancar tampoco sirve: cambiaría en cada reinicio, y con dos
procesos cada uno rechazaría los tokens del otro.
"""

from functools import lru_cache

from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Base de datos -------------------------------------------------------------
    POSTGRES_USER: str = "taller"
    POSTGRES_PASSWORD: SecretStr = Field(min_length=1)  # obligatoria, sin default
    POSTGRES_DB: str = "taller"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DRIVER: str = "postgresql+asyncpg"

    DB_POOL_SIZE: int = Field(default=5, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0)
    SQL_ECHO: bool = False  # muestra las consultas en la consola (evidencia de C-15)

    # --- Token ---------------------------------------------------------------------
    JWT_SECRET: SecretStr = Field(min_length=32)  # obligatoria, sin default
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRA_MINUTOS: int = Field(default=30, ge=1)
    COOKIE_SECURE: bool = False  # en producción, con HTTPS, va en true

    # --- Contraseñas ---------------------------------------------------------------
    # El costo se declara acá y no en el código: es un valor que se sube con los años
    # (secciones 5.4 y 5.12).
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=31)
    BCRYPT_CONCURRENCIA: int = Field(default=4, ge=1)

    # --- Límite de intentos de login (RN-08) ---------------------------------------
    LOGIN_MAX_FALLOS: int = Field(default=5, ge=1)
    LOGIN_VENTANA_SEGUNDOS: int = Field(default=60, ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        # URL.create escapa la contraseña: un «@» o una «/» no rompen la dirección.
        return URL.create(
            drivername=self.POSTGRES_DRIVER,
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    @property
    def jwt_expira_segundos(self) -> int:
        return self.JWT_EXPIRA_MINUTOS * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
