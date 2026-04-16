
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import CacheBackend, create_cache_backend
from ..core.config import settings
from ..core.database import get_db
from ..core.security import decode_access_token
from ..data.models.user import User
from ..data.repositories.book_repository import BookRepository
from ..data.repositories.user_repository import UserRepository
from ..domain.exceptions import (
    AuthenticationException,
    AuthorizationException,
    UserInactiveException,
)
from ..domain.services.auth_service import AuthService
from ..domain.services.book_service import BookService
from ..external.openlibrary.client import OpenLibraryClient

auth_scheme = HTTPBearer(auto_error=False)


# ========== EXTERNAL CLIENTS (Singletons) ==========

@lru_cache
def get_cache_backend() -> CacheBackend:
    """Get singleton cache backend."""
    return create_cache_backend(
        backend=settings.cache_backend,
        redis_url=settings.redis_url,
    )


@lru_cache
def get_openlibrary_client() -> OpenLibraryClient:
    """
    Получить singleton OpenLibraryClient.
    
    lru_cache создает клиент один раз и переиспользует.
    """
    return OpenLibraryClient(
        base_url=settings.openlibrary_base_url,
        timeout=settings.openlibrary_timeout,
        cache=get_cache_backend(),
        cache_ttl=settings.openlibrary_cache_ttl,
    )


# ========== REPOSITORIES ==========

async def get_book_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> BookRepository:
    """
    Создать BookRepository для текущей сессии БД.
    
    Создается новый экземпляр для каждого запроса.
    """
    return BookRepository(db)


async def get_user_repository(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> UserRepository:
    """Create UserRepository for the current DB session."""
    return UserRepository(db)


# ========== SERVICES ==========

async def get_book_service(
    book_repo: Annotated[BookRepository, Depends(get_book_repository)],
    ol_client: Annotated[OpenLibraryClient, Depends(get_openlibrary_client)],
    cache: Annotated[CacheBackend, Depends(get_cache_backend)],
) -> BookService:
    """
    Создать BookService с внедренными зависимостями.
    
    FastAPI автоматически разрешит все зависимости:
    1. get_db() создаст AsyncSession
    2. get_book_repository() создаст BookRepository с session
    3. get_openlibrary_client() вернет singleton клиент
    4. Все внедрится в BookService
    """
    return BookService(
        book_repository=book_repo,
        openlibrary_client=ol_client,
        cache=cache,
        search_cache_ttl=settings.search_cache_ttl,
    )


async def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    """Create AuthService with required dependencies."""
    return AuthService(
        user_repository=user_repo,
        jwt_secret_key=settings.jwt_secret_key,
        jwt_access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(auth_scheme),
    ],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> User:
    """Get current authenticated user from JWT token."""
    if credentials is None:
        raise AuthenticationException("Authentication credentials were not provided")

    try:
        payload = decode_access_token(credentials.credentials, settings.jwt_secret_key)
    except ValueError as exc:
        raise AuthenticationException(str(exc)) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationException("Invalid token payload")

    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise AuthenticationException("Invalid token subject") from exc

    user = await user_repo.get_by_id(user_uuid)
    if user is None:
        raise AuthenticationException("User not found")

    if not user.is_active:
        raise UserInactiveException()

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure current user has admin role."""
    if current_user.role != "admin":
        raise AuthorizationException()
    return current_user


# ========== TYPE ALIASES ДЛЯ УДОБСТВА ==========

# Можно использовать в роутерах так:
# async def my_route(service: BookServiceDep):
BookServiceDep = Annotated[BookService, Depends(get_book_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
BookRepoDep = Annotated[BookRepository, Depends(get_book_repository)]
UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
AdminUserDep = Annotated[User, Depends(get_current_admin_user)]
