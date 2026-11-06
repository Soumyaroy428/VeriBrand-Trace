"""Workspace multi-tenant management endpoints and member administration."""

import re
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.dependencies import get_current_user, require_workspace_role
from app.models.documents import User, Workspace, Membership, AuditEvent
from app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    MembershipCreateRequest,
    MembershipResponse,
)

router = APIRouter()


def slugify(text: str) -> str:
    """Generates an alphanumeric URL slug from a name."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")


@router.get("", response_model=List[WorkspaceResponse])
async def list_user_workspaces(current_user: User = Depends(get_current_user)):
    """List all brand workspaces accessible to the authenticated user."""
    memberships = await Membership.find(Membership.user_id == current_user.id).to_list()
    
    workspaces = []
    for m in memberships:
        ws = await Workspace.get(m.workspace_id)
        if ws and ws.status == "ACTIVE":
            workspaces.append(
                WorkspaceResponse(
                    id=ws.id,
                    name=ws.name,
                    slug=ws.slug,
                    status=ws.status,
                    current_user_role=m.role,
                    created_at=ws.created_at,
                )
            )
    return workspaces


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new brand workspace. The creating user automatically becomes GOVERNANCE_ADMIN."""
    slug = request.slug or slugify(request.name)
    existing_slug = await Workspace.find_one(Workspace.slug == slug)
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "SLUG_CONFLICT", "message": f"Workspace slug '{slug}' is already taken"}},
        )

    workspace = Workspace(
        name=request.name,
        slug=slug,
        status="ACTIVE",
    )
    await workspace.insert()

    # Assign Creator as GOVERNANCE_ADMIN
    membership = Membership(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="GOVERNANCE_ADMIN",
    )
    await membership.insert()

    # Cryptographic Audit Event
    created_at_now = datetime.now(timezone.utc)
    created_at_iso = created_at_now.isoformat()
    event_hash = AuditEvent.calculate_hash(
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        entity_type="WORKSPACE",
        entity_id=workspace.id,
        action="WORKSPACE_CREATED",
        metadata_json={"name": workspace.name, "slug": workspace.slug},
        previous_hash=None,
        created_at_iso=created_at_iso,
    )
    audit_event = AuditEvent(
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        entity_type="WORKSPACE",
        entity_id=workspace.id,
        action="WORKSPACE_CREATED",
        metadata_json={"name": workspace.name, "slug": workspace.slug},
        previous_hash=None,
        event_hash=event_hash,
        created_at=created_at_now,
    )
    await audit_event.insert()

    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        status=workspace.status,
        current_user_role="GOVERNANCE_ADMIN",
        created_at=workspace.created_at,
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """Retrieve details for a specific brand workspace (accessible to any workspace member)."""
    ws = await Workspace.get(workspace_id)
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        status=ws.status,
        current_user_role=membership.role,
        created_at=ws.created_at,
    )


@router.get("/{workspace_id}/members", response_model=List[MembershipResponse])
async def list_workspace_members(
    workspace_id: str,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
):
    """List all members of a workspace. Restricted to GOVERNANCE_ADMIN."""
    memberships = await Membership.find(Membership.workspace_id == workspace_id).to_list()
    
    responses = []
    for m in memberships:
        user = await User.get(m.user_id)
        if user:
            responses.append(
                MembershipResponse(
                    id=m.id,
                    workspace_id=m.workspace_id,
                    user_id=user.id,
                    user_email=user.email,
                    user_name=user.full_name,
                    role=m.role,
                    created_at=m.created_at,
                )
            )
    return responses


@router.post("/{workspace_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: str,
    request: MembershipCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Assign or invite a user to the workspace. Restricted to GOVERNANCE_ADMIN."""
    target_user = await User.find_one(User.email == request.user_email.lower())
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "USER_NOT_FOUND", "message": f"User with email {request.user_email} not found"}},
        )

    # Check existing membership
    existing_member = await Membership.find_one(
        Membership.workspace_id == workspace_id,
        Membership.user_id == target_user.id,
    )
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "ALREADY_MEMBER", "message": "User is already a member of this workspace"}},
        )

    new_member = Membership(
        workspace_id=workspace_id,
        user_id=target_user.id,
        role=request.role,
    )
    await new_member.insert()

    # Record tamper-evident audit event
    created_at_now = datetime.now(timezone.utc)
    created_at_iso = created_at_now.isoformat()
    last_event = await AuditEvent.find(
        AuditEvent.workspace_id == workspace_id
    ).sort("-created_at").first_or_none()
    previous_hash = last_event.event_hash if last_event else None

    event_hash = AuditEvent.calculate_hash(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="MEMBERSHIP",
        entity_id=new_member.id,
        action="MEMBER_ADDED",
        metadata_json={"user_email": target_user.email, "role": request.role},
        previous_hash=previous_hash,
        created_at_iso=created_at_iso,
    )
    audit_event = AuditEvent(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="MEMBERSHIP",
        entity_id=new_member.id,
        action="MEMBER_ADDED",
        metadata_json={"user_email": target_user.email, "role": request.role},
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at_now,
    )
    await audit_event.insert()

    return MembershipResponse(
        id=new_member.id,
        workspace_id=new_member.workspace_id,
        user_id=target_user.id,
        user_email=target_user.email,
        user_name=target_user.full_name,
        role=new_member.role,
        created_at=new_member.created_at,
    )

