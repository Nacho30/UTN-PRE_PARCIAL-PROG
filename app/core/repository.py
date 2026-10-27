"""`BaseRepository[T]` y `SoftDeleteRepository[T]` (arquitectura en capas).

Ningún repositorio hace `commit()`, sólo `flush()` para que las restricciones se evalúen
dentro de la transacción abierta por el Unit of Work.
"""

from typing import Generic, Sequence, TypeVar
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.core.tipos import ahora

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Repositorio base con operaciones CRUD elementales."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> T | None:
        stmt = select(self.model).where(getattr(self.model, "id") == id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self) -> Sequence[T]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T) -> T:
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()


class SoftDeleteRepository(BaseRepository[T]):
    """Repositorio para entidades con borrado lógico (`borrado_en`)."""

    async def get_by_id(self, id: int) -> T | None:
        stmt = select(self.model).where(
            getattr(self.model, "id") == id,
            getattr(self.model, "borrado_en").is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_including_deleted(self, id: int) -> T | None:
        return await super().get_by_id(id)

    async def get_all(self) -> Sequence[T]:
        stmt = select(self.model).where(getattr(self.model, "borrado_en").is_(None))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model).where(getattr(self.model, "borrado_en").is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def soft_delete(self, entity: T) -> None:
        setattr(entity, "borrado_en", ahora())
        await self.session.flush()
