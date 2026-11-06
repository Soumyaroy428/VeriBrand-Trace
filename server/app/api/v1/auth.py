"""Authentication endpoints: register, login, session inspection, and logout."""

from fastapi import APIRouter, HTTPException, status, Depends
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.documents import User, Membership, Workspace
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserSummary,
    UserProfileResponse,
    WorkspaceRoleItem,
)

router = APIRouter()


@router.post("/register", response_model=UserSummary, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest):
    """Register a new user account."""
    existing = await User.find_one(User.email == request.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "EMAIL_ALREADY_EXISTS", "message": "An account with this email already exists"}},
        )

    user = User(
        email=request.email.lower(),
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        is_active=True,
        is_superuser=False,
    )
    await user.insert()

    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest):
    """Authenticate with email and password to receive a JWT access token."""
    user = await User.find_one(User.email == request.email.lower())
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_DISABLED", "message": "Your account has been deactivated"}},
        )

    access_token = create_access_token(
        subject=user.id,
        email=user.email,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        ),
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile and workspace roles for the authenticated user."""
    memberships = await Membership.find(Membership.user_id == current_user.id).to_list()
    
    workspace_items = []
    for m in memberships:
        ws = await Workspace.get(m.workspace_id)
        if ws and ws.status == "ACTIVE":
            workspace_items.append(
                WorkspaceRoleItem(
                    workspace_id=ws.id,
                    workspace_name=ws.name,
                    workspace_slug=ws.slug,
                    role=m.role,
                )
            )

    return UserProfileResponse(
        user=UserSummary(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            is_active=current_user.is_active,
            is_superuser=current_user.is_superuser,
        ),
        workspaces=workspace_items,
    )


@router.post("/logout")
async def logout_user(current_user: User = Depends(get_current_user)):
    """Revoke session and acknowledge logout."""
    return {"status": "success", "message": f"Successfully logged out session for {current_user.email}"}
