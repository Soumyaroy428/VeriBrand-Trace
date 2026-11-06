"""Pydantic schemas for multi-tenant workspace management."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: Optional[str] = Field(None, max_length=100)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    current_user_role: Optional[str] = None
    created_at: datetime


class MembershipCreateRequest(BaseModel):
    user_email: EmailStr
    role: str = Field("CREATOR", pattern="^(CREATOR|REVIEWER|GOVERNANCE_ADMIN)$")


class MembershipResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    user_email: str
    user_name: Optional[str] = None
    role: str
    created_at: datetime
