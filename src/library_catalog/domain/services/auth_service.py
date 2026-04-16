from ...core.security import create_access_token, hash_password, verify_password
from ...data.models.user import User
from ...data.repositories.user_repository import UserRepository
from ..exceptions import AuthenticationException, UserAlreadyExistsException


class AuthService:
    """Service layer for registration and authentication."""

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_secret_key: str,
        jwt_access_token_expire_minutes: int,
    ):
        self.user_repo = user_repository
        self.jwt_secret_key = jwt_secret_key
        self.jwt_access_token_expire_minutes = jwt_access_token_expire_minutes

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        role: str = "user",
    ) -> User:
        """Register a new user."""
        existing_by_email = await self.user_repo.find_by_email(email)
        if existing_by_email is not None:
            raise UserAlreadyExistsException(email)

        existing_by_username = await self.user_repo.find_by_username(username)
        if existing_by_username is not None:
            raise UserAlreadyExistsException(username)

        return await self.user_repo.create(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )

    async def authenticate_user(self, email: str, password: str) -> User:
        """Authenticate user by email and password."""
        user = await self.user_repo.find_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationException()
        return user

    def create_token_for_user(self, user: User) -> str:
        """Create JWT access token for user."""
        return create_access_token(
            subject=str(user.user_id),
            role=user.role,
            secret_key=self.jwt_secret_key,
            expires_minutes=self.jwt_access_token_expire_minutes,
        )
