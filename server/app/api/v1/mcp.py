"""Model Context Protocol (MCP) API Endpoints.

Provides standardized, authenticated MCP tool invocation for external LLMs,
AI agents, and IDE extensions (Cursor, Claude Desktop, Antigravity, VS Code).
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Header

from app.core.dependencies import get_current_user
from app.models.documents import User, Membership
from app.schemas.mcp import (
    MCPToolDefinition,
    MCPToolCallRequest,
    MCPToolCallResponse,
)
from app.services.mcp_service import mcp_service

router = APIRouter()


async def verify_mcp_access(workspace_id: str, user: User) -> Membership:
    """Verifies that the calling identity is a recognized workspace member."""
    membership = await Membership.find_one(
        Membership.workspace_id == workspace_id,
        Membership.user_id == user.id,
    )
    if not membership and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: caller is not a member of this brand workspace",
        )
    return membership


@router.get(
    "/mcp/tools/list",
    response_model=List[MCPToolDefinition],
    summary="List available Model Context Protocol brand governance tools",
)
async def list_mcp_tools():
    """Returns the schema and definitions of all available MCP tools."""
    return mcp_service.list_tools()


@router.post(
    "/workspaces/{workspace_id}/mcp/tools/call",
    response_model=MCPToolCallResponse,
    summary="Invoke an MCP brand governance tool within workspace scope",
)
async def call_mcp_tool(
    workspace_id: str,
    payload: MCPToolCallRequest,
    current_user: User = Depends(get_current_user),
):
    """Executes a scoped MCP tool, strictly enforcing RBAC and human-in-the-loop safety gates."""
    await verify_mcp_access(workspace_id, current_user)

    return await mcp_service.execute_tool(
        workspace_id=workspace_id,
        user_id=current_user.id,
        tool_name=payload.tool,
        arguments=payload.arguments,
    )
