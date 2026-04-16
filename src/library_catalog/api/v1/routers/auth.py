from fastapi import APIRouter, status

from ..schemas.auth import AuthResponse, UserLogin, UserRegister, UserResponse
from ...dependencies import AuthServiceDep, CurrentUserDep

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
)
async def register_user(
    user_data: UserRegister,
    service: AuthServiceDep,
):
    """Register a new user."""
    user = await service.register_user(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        role=user_data.role,
    )
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login user",
)
async def login_user(
    credentials: UserLogin,
    service: AuthServiceDep,
):
    """Authenticate user and return access token."""
    user = await service.authenticate_user(credentials.email, credentials.password)
    token = service.create_token_for_user(user)
    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_profile(
    current_user: CurrentUserDep,
):
    """Return current authenticated user."""
    return UserResponse.model_validate(current_user)
