"""Envoltorio de los listados `{items, total, page, size, pages}` y cálculo de páginas."""

import math
from typing import Any, Generic, TypeVar
from fastapi import Query
from sqlmodel import SQLModel

from app.core.errores import ErrorPaginacion

T = TypeVar("T")


class Pagina(SQLModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class ParametrosPagina:
    """Parámetros de consulta estándar para paginación."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, le=2_147_483_647, description="Número de página (>= 1)"),
        size: int = Query(default=20, ge=1, le=100, description="Cantidad de elementos por página (1..100)"),
    ):
        # Compatibilidad tanto para inyección de FastAPI como para instanciación directa
        self.page: int = page.default if hasattr(page, "default") and not isinstance(page, int) else int(page)
        self.size: int = size.default if hasattr(size, "default") and not isinstance(size, int) else int(size)


def calcular_paginacion(total: int, params: ParametrosPagina) -> tuple[int, int, int]:
    """Calcula (page, size, pages).

    Si page > pages, lanza ErrorPaginacion con «La página N no existe: hay M».
    Con total == 0, pages es 1: page=1 devuelve lista vacía y page >= 2 da 422.
    """
    pages = max(1, math.ceil(total / params.size))
    if params.page > pages:
        raise ErrorPaginacion(f"La página {params.page} no existe: hay {pages}")
    return params.page, params.size, pages
