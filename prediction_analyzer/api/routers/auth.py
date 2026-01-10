# prediction_analyzer/api/routers/auth.py
"""
Authentication endpoints - signup, login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..schemas.user import UserCreate, UserResponse
from ..schemas.auth import Token
from ..services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    Returns the created user and an access token.
    """
    # Check if email already exists
    if auth_service.get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    if auth_service.get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    user = auth_service.create_user(
        db,
        email=user_data.email,
        username=user_data.username,
        password=user_data.password
    )

    # Create access token
    access_token = auth_service.create_access_token(data={"sub": user.id})

    return {
        "user": UserResponse.model_validate(user),
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Account created successfully"
    }


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return access token.

    Uses OAuth2 password flow - username field should contain email.
    """
    user = auth_service.authenticate_user(
        db,
        email=form_data.username,  # OAuth2 uses 'username' field
        password=form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = auth_service.create_access_token(data={"sub": user.id})

    return Token(access_token=access_token, token_type="bearer")


@router.post("/login/json", response_model=Token)
async def login_json(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    """
    Alternative JSON-based login endpoint.

    Accepts email and password as JSON body instead of form data.
    """
    user = auth_service.authenticate_user(db, email=email, password=password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    access_token = auth_service.create_access_token(data={"sub": user.id})

    return Token(access_token=access_token, token_type="bearer")
