from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BookBase(BaseModel):
    """Shared fields for book input schemas."""

    title: str
    author: str
    year: int
    genre: str
    pages: int
    isbn: str | None = None
    description: str | None = None


class BookCreate(BookBase):
    """Schema for creating a book."""


class BookUpdate(BaseModel):
    """Schema for partially updating a book."""

    title: str | None = None
    author: str | None = None
    year: int | None = None
    genre: str | None = None
    pages: int | None = None
    available: bool | None = None
    isbn: str | None = None
    description: str | None = None
    extra: dict | None = None


class ShowBook(BaseModel):
    """Schema for returning book data from the API."""

    book_id: UUID
    title: str
    author: str
    year: int
    genre: str
    pages: int
    available: bool
    isbn: str | None = None
    description: str | None = None
    extra: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
