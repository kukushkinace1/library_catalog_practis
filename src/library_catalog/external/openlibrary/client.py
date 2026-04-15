from ..base.base_client import BaseApiClient
from ...domain.exceptions import OpenLibraryException, OpenLibraryTimeoutException
import httpx
from pydantic import ValidationError

from .schemas import OpenLibrarySearchResponse

class OpenLibraryClient(BaseApiClient):
    """Клиент для Open Library API."""
    
    def __init__(
        self,
        base_url: str = "https://openlibrary.org",
        timeout: float = 10.0,
    ):
        super().__init__(base_url, timeout=timeout)
    
    def client_name(self) -> str:
        return "openlibrary"
    
    async def search_by_isbn(self, isbn: str) -> dict:
        """
        Поиск книги по ISBN.
        
        Args:
            isbn: ISBN-10 или ISBN-13
            
        Returns:
            dict: Данные книги (cover_url, subjects, etc.)
            
        Raises:
            OpenLibraryException: При ошибке API
        """
        try:
            data = await self._get(
                "/search.json",
                params={"isbn": isbn, "limit": 1}
            )

            response = OpenLibrarySearchResponse.model_validate(data)
            if not response.docs:
                return {}

            return self._extract_book_data(
                response.docs[0].model_dump(by_alias=True)
            )
        
        except httpx.TimeoutException:
            raise OpenLibraryTimeoutException(self.timeout)
        except httpx.HTTPError as e:
            raise OpenLibraryException(str(e))
        except ValidationError as e:
            raise OpenLibraryException(f"Invalid Open Library response: {e}")
    
    async def search_by_title_author(
        self,
        title: str,
        author: str
    ) -> dict:
        """Поиск по названию и автору."""
        try:
            data = await self._get(
                "/search.json",
                params={
                    "title": title,
                    "author": author,
                    "limit": 1
                }
            )

            response = OpenLibrarySearchResponse.model_validate(data)
            if not response.docs:
                return {}

            return self._extract_book_data(
                response.docs[0].model_dump(by_alias=True)
            )
        
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
        """
        Обогатить данные книги.
        
        Сначала пытается найти по ISBN, затем по title+author.
        
        Returns:
            dict: Обогащенные данные или пустой словарь
        """
        # Попытка 1: По ISBN
        if isbn:
            data = await self.search_by_isbn(isbn)
            if data:
                return data
        
        # Попытка 2: По title + author
        return await self.search_by_title_author(title, author)
    
    def _extract_book_data(self, doc: dict) -> dict:
        """
        Извлечь нужные поля из ответа Open Library.
        
        Args:
            doc: Документ из массива docs
            
        Returns:
            dict: Обработанные данные
        """
        result = {}
        
        # Cover URL
        if cover_id := doc.get("cover_i"):
            result["cover_url"] = self._get_cover_url(cover_id)
        
        # Subjects (темы)
        if subjects := doc.get("subject"):
            result["subjects"] = subjects[:10]  # Первые 10
        
        # Publisher
        if publisher := doc.get("publisher"):
            result["publisher"] = publisher[0]
        
        # Language
        if language := doc.get("language"):
            result["language"] = language[0]
        
        # Ratings
        ratings = doc.get("ratings_average")
        if ratings is not None:
            result["rating"] = ratings
        
        return result
    
    def _get_cover_url(self, cover_id: int | None) -> str | None:
        """Получить URL обложки."""
        if not cover_id:
            return None
        return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
