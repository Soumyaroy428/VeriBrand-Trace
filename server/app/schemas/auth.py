"""Pydantic schemas for authentication and user management."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password minimum 8 characters")
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserSummary(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


class WorkspaceRoleItem(BaseModel):
    workspace_id: str
    workspace_name: str
    workspace_slug: str
    role: str


class UserProfileResponse(BaseModel):
    user: UserSummary
    workspaces: List[WorkspaceRoleItem]

