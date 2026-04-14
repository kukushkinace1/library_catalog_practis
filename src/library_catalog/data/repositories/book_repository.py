from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.book import Book
from .base_repository import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Repository with book-specific query helpers."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Book)

    def _apply_filters(
        self,
        stmt,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
    ):
        if title is not None:
            stmt = stmt.where(Book.title.ilike(f"%{title}%"))
        if author is not None:
            stmt = stmt.where(Book.author.ilike(f"%{author}%"))
        if genre is not None:
            stmt = stmt.where(Book.genre.ilike(f"%{genre}%"))
        if year is not None:
            stmt = stmt.where(Book.year == year)
        if available is not None:
            stmt = stmt.where(Book.available == available)
        return stmt

    async def find_by_filters(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Book]:
        """Search books using optional filters."""
        stmt = select(Book)
        stmt = self._apply_filters(
            stmt,
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
        )
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_isbn(self, isbn: str) -> Book | None:
        """Find a book by ISBN."""
        stmt = select(Book).where(Book.isbn == isbn)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_filters(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
    ) -> int:
        """Count books matching optional filters."""
        stmt = select(func.count()).select_from(Book)
        stmt = self._apply_filters(
            stmt,
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
        )

        result = await self.session.execute(stmt)
        return int(result.scalar_one())
