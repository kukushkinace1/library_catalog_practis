import hashlib
import json
import logging
from uuid import UUID

from ...api.v1.schemas.book import BookCreate, BookUpdate, ShowBook
from ...core.cache import CacheBackend
from ...data.repositories.book_repository import BookRepository
from ...external.openlibrary.client import OpenLibraryClient
from ..exceptions import *
from ..mappers.book_mapper import BookMapper

logger = logging.getLogger(__name__)


class BookService:
    """Service layer for books."""

    def __init__(
        self,
        book_repository: BookRepository,
        openlibrary_client: OpenLibraryClient,
        cache: CacheBackend | None = None,
        search_cache_ttl: int = 300,
    ):
        self.book_repo = book_repository
        self.ol_client = openlibrary_client
        self.cache = cache
        self.search_cache_ttl = search_cache_ttl

    async def create_book(self, book_data: BookCreate) -> ShowBook:
        """Create a new book with optional Open Library enrichment."""
        self._validate_book_data(book_data)

        if book_data.isbn:
            existing = await self.book_repo.find_by_isbn(book_data.isbn)
            if existing:
                raise BookAlreadyExistsException(book_data.isbn)

        extra = await self._enrich_book_data(book_data) or {}

        book = await self.book_repo.create(
            title=book_data.title,
            author=book_data.author,
            year=book_data.year,
            genre=book_data.genre,
            pages=book_data.pages,
            isbn=book_data.isbn,
            description=book_data.description,
            extra=extra,
        )
        await self._invalidate_search_cache()
        return BookMapper.to_show_book(book)

    async def get_book(self, book_id: UUID) -> ShowBook:
        """Get a book by id."""
        book = await self.book_repo.get_by_id(book_id)
        if book is None:
            raise BookNotFoundException(book_id)

        return BookMapper.to_show_book(book)

    async def update_book(
        self,
        book_id: UUID,
        book_data: BookUpdate,
    ) -> ShowBook:
        """Partially update a book."""
        existing = await self.book_repo.get_by_id(book_id)
        if existing is None:
            raise BookNotFoundException(book_id)

        if book_data.year is not None:
            self._validate_year(book_data.year)
        if book_data.pages is not None:
            self._validate_pages(book_data.pages)

        updated = await self.book_repo.update(
            book_id,
            **book_data.model_dump(exclude_unset=True),
        )
        await self._invalidate_search_cache()
        return BookMapper.to_show_book(updated)

    async def delete_book(self, book_id: UUID) -> None:
        """Delete a book by id."""
        deleted = await self.book_repo.delete(book_id)
        if not deleted:
            raise BookNotFoundException(book_id)
        await self._invalidate_search_cache()

    async def search_books(
        self,
        title: str | None = None,
        author: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        available: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ShowBook], int]:
        """Search books with filters and pagination."""
        cache_key = self._build_search_cache_key(
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
            limit=limit,
            offset=offset,
        )
        cached_result = await self._get_cached_search_result(cache_key)
        if cached_result is not None:
            return cached_result

        books = await self.book_repo.find_by_filters(
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
            limit=limit,
            offset=offset,
        )

        total = await self.book_repo.count_by_filters(
            title=title,
            author=author,
            genre=genre,
            year=year,
            available=available,
        )

        show_books = BookMapper.to_show_books(books)
        await self._set_cached_search_result(cache_key, show_books, total)
        return show_books, total

    def _validate_book_data(self, data: BookCreate) -> None:
        """Validate business rules for a new book."""
        self._validate_year(data.year)
        self._validate_pages(data.pages)

    def _validate_year(self, year: int) -> None:
        """Validate publication year."""
        from datetime import datetime

        current_year = datetime.now().year
        if year < 1000 or year > current_year:
            raise InvalidYearException(year)

    def _validate_pages(self, pages: int) -> None:
        """Validate page count."""
        if pages <= 0:
            raise InvalidPagesException(pages)

    async def _enrich_book_data(
        self,
        book_data: BookCreate,
    ) -> dict | None:
        """Enrich book data using Open Library without breaking creation."""
        try:
            extra = await self.ol_client.enrich(
                title=book_data.title,
                author=book_data.author,
                isbn=book_data.isbn,
            )
            return extra if extra else None
        except (OpenLibraryException, OpenLibraryTimeoutException):
            logger.warning(
                "Failed to enrich book data from Open Library",
                extra={"title": book_data.title, "author": book_data.author},
            )
            return None

    def _build_search_cache_key(self, **params) -> str:
        """Build deterministic cache key for search results."""
        payload = json.dumps(params, sort_keys=True, ensure_ascii=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"book-search:{digest}"

    async def _get_cached_search_result(
        self,
        cache_key: str,
    ) -> tuple[list[ShowBook], int] | None:
        """Read cached search results."""
        if self.cache is None:
            return None

        cached = await self.cache.get(cache_key)
        if cached is None:
            return None

        items = [ShowBook.model_validate(item) for item in cached["items"]]
        return items, int(cached["total"])

    async def _set_cached_search_result(
        self,
        cache_key: str,
        books: list[ShowBook],
        total: int,
    ) -> None:
        """Save search results to cache."""
        if self.cache is None:
            return

        payload = {
            "items": [book.model_dump(mode="json") for book in books],
            "total": total,
        }
        await self.cache.set(cache_key, payload, ttl=self.search_cache_ttl)

    async def _invalidate_search_cache(self) -> None:
        """Invalidate cached search results after mutations."""
        if self.cache is None:
            return
        await self.cache.delete_by_prefix("book-search:")
