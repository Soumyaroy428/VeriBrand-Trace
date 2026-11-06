"""FastAPI dependency injection for authentication and workspace RBAC enforcement."""

from typing import Callable, Sequence, Any, List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.models.documents import User, Membership, Workspace

security_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> User:
    """Validates JWT access token and resolves current authenticated user."""
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHENTICATED", "message": str(e)}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token missing subject claim"}},
        )

    user = await User.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User account is inactive or not found"}},
        )

    return user


def require_workspace_role(*allowed_roles: Any) -> Callable:
    """Enforces that the current authenticated user belongs to the requested workspace
    and possesses one of the authorized roles (CREATOR, REVIEWER, GOVERNANCE_ADMIN).
    Superusers automatically bypass workspace membership checks.
    Supports either positional args ("ROLE1", "ROLE2") or a single list (["ROLE1", "ROLE2"]).
    """
    flat_roles: List[str] = []
    for r in allowed_roles:
        if isinstance(r, (list, tuple)):
            flat_roles.extend(r)
        else:
            flat_roles.append(r)

    async def _workspace_role_verifier(
        workspace_id: str,
        current_user: User = Depends(get_current_user),
    ) -> Membership:
        # Check that workspace exists
        workspace = await Workspace.get(workspace_id)
        if not workspace or workspace.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "WORKSPACE_NOT_FOUND", "message": "Workspace not found or inactive"}},
            )

        # Superuser bypass
        if current_user.is_superuser:
            return Membership(
                workspace_id=workspace_id,
                user_id=current_user.id,
                role="GOVERNANCE_ADMIN",
            )

        # Query membership
        membership = await Membership.find_one(
            Membership.workspace_id == workspace_id,
            Membership.user_id == current_user.id,
        )

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "You are not an authorized member of this brand workspace",
                    }
                },
            )

        # Enforce Role-Based Access Control
        if flat_roles and membership.role not in flat_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": f"Action requires one of {flat_roles}. Your current role is {membership.role}.",
                    }
                },
            )

        return membership

    return _workspace_role_verifier

