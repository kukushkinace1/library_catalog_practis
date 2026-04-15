import hashlib
import json

import httpx
from pydantic import ValidationError

from ..base.base_client import BaseApiClient
from ...core.cache import CacheBackend
from ...domain.exceptions import OpenLibraryException, OpenLibraryTimeoutException
from .schemas import OpenLibrarySearchResponse


class OpenLibraryClient(BaseApiClient):
    """Client for the Open Library API."""

    def __init__(
        self,
        base_url: str = "https://openlibrary.org",
        timeout: float = 10.0,
        cache: CacheBackend | None = None,
        cache_ttl: int = 3600,
    ):
        super().__init__(base_url, timeout=timeout)
        self.cache = cache
        self.cache_ttl = cache_ttl

    def client_name(self) -> str:
        return "openlibrary"

    async def search_by_isbn(self, isbn: str) -> dict:
        """Search a book by ISBN."""
        cache_key = self._build_cache_key(
            "openlibrary:isbn",
            {"isbn": isbn},
        )
        cached_data = await self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            data = await self._get(
                "/search.json",
                params={"isbn": isbn, "limit": 1},
            )

            response = OpenLibrarySearchResponse.model_validate(data)
            if not response.docs:
                await self._set_cached_data(cache_key, {})
                return {}

            book_data = self._extract_book_data(
                response.docs[0].model_dump(by_alias=True)
            )
            await self._set_cached_data(cache_key, book_data)
            return book_data

        except httpx.TimeoutException:
            raise OpenLibraryTimeoutException(self.timeout)
        except httpx.HTTPError as e:
            raise OpenLibraryException(str(e))
        except ValidationError as e:
            raise OpenLibraryException(f"Invalid Open Library response: {e}")

    async def search_by_title_author(
        self,
        title: str,
        author: str,
    ) -> dict:
        """Search a book by title and author."""
        cache_key = self._build_cache_key(
            "openlibrary:title-author",
            {"title": title, "author": author},
        )
        cached_data = await self._get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            data = await self._get(
                "/search.json",
                params={
                    "title": title,
                    "author": author,
                    "limit": 1,
                },
            )

            response = OpenLibrarySearchResponse.model_validate(data)
            if not response.docs:
                await self._set_cached_data(cache_key, {})
                return {}

            book_data = self._extract_book_data(
                response.docs[0].model_dump(by_alias=True)
            )
            await self._set_cached_data(cache_key, book_data)
            return book_data

        except httpx.TimeoutException:
            raise OpenLibraryTimeoutException(self.timeout)
        except httpx.HTTPError as e:
            raise OpenLibraryException(str(e))
        except ValidationError as e:
            raise OpenLibraryException(f"Invalid Open Library response: {e}")

    async def enrich(
        self,
        title: str,
        author: str,
        isbn: str | None = None,
    ) -> dict:
        """Enrich book data using Open Library."""
        if isbn:
            data = await self.search_by_isbn(isbn)
            if data:
                return data

        return await self.search_by_title_author(title, author)

    def _extract_book_data(self, doc: dict) -> dict:
        """Extract the fields used by the application."""
        result = {}

        if cover_id := doc.get("cover_i"):
            result["cover_url"] = self._get_cover_url(cover_id)

        if subjects := doc.get("subject"):
            result["subjects"] = subjects[:10]

        if publisher := doc.get("publisher"):
            result["publisher"] = publisher[0]

        if language := doc.get("language"):
            result["language"] = language[0]

        ratings = doc.get("ratings_average")
        if ratings is not None:
            result["rating"] = ratings

        return result

    def _get_cover_url(self, cover_id: int | None) -> str | None:
        """Build cover image URL."""
        if not cover_id:
            return None
        return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

    def _build_cache_key(self, prefix: str, params: dict) -> str:
        """Build deterministic cache key for Open Library requests."""
        payload = json.dumps(params, sort_keys=True, ensure_ascii=True)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{prefix}:{digest}"

    async def _get_cached_data(self, key: str) -> dict | None:
        """Get cached Open Library response."""
        if self.cache is None:
            return None
        cached = await self.cache.get(key)
        if cached is None:
            return None
        return cached

    async def _set_cached_data(self, key: str, value: dict) -> None:
        """Save Open Library response to cache."""
        if self.cache is None:
            return
        await self.cache.set(key, value, ttl=self.cache_ttl)
