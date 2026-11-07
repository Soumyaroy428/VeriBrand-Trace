"""Pydantic schemas for Model Context Protocol (MCP) tool invocation and discovery."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MCPToolParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: List[MCPToolParameter]
    required_role: str = "CREATOR"


class MCPToolCallRequest(BaseModel):
    """Payload to execute an MCP tool in a workspace context."""
    tool: str = Field(..., description="Name of the MCP tool to invoke")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class MCPToolCallResponse(BaseModel):
    """Structured response returned to an MCP client."""
    tool: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    audit_event_id: Optional[str] = None
