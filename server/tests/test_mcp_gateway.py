"""Model Context Protocol (MCP) Gateway Integration Tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.documents import User, Workspace, Membership, ApprovedFact, TerminologyRule, AuditEvent
from app.core.security import create_access_token


@pytest.fixture
async def setup_mcp_test_env():
    """Sets up a workspace, member user, and auth headers for MCP tests."""
    ws = Workspace(name="MCP Integration Workspace", slug="mcp-test-ws")
    await ws.insert()

    user = User(
        email="mcp_agent_dev@veribrand.io",
        hashed_password="TestPassword123",
        full_name="AI Agent Developer",
        is_active=True,
    )
    await user.insert()

    membership = Membership(
        workspace_id=ws.id,
        user_id=user.id,
        role="CREATOR",
    )
    await membership.insert()

    # Seed an approved fact and terminology rule
    fact = ApprovedFact(
        workspace_id=ws.id,
        fact_key="global_latency",
        statement="Certified latency is below 15ms across 99% of global regions.",
        created_by=user.id,
    )
    await fact.insert()

    term = TerminologyRule(
        workspace_id=ws.id,
        term="cheap",
        rule_type="BANNED",
        replacement="cost-effective",
        created_by=user.id,
    )
    await term.insert()

    token = create_access_token(subject=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    return {"workspace": ws, "user": user, "headers": headers}


@pytest.mark.asyncio
async def test_list_mcp_tools():
    """Verifies that all 6 brand governance tools are advertised in the MCP catalogue."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/mcp/tools/list")

    assert res.status_code == 200
    tools = res.json()
    tool_names = [t["name"] for t in tools]
    assert "get_brand_rules" in tool_names
    assert "search_approved_facts" in tool_names
    assert "audit_text" in tool_names
    assert "get_audit_findings" in tool_names
    assert "request_exception" in tool_names
    assert "get_review_status" in tool_names


@pytest.mark.asyncio
async def test_mcp_search_approved_facts(setup_mcp_test_env):
    """Verifies an external AI agent querying approved facts via MCP."""
    env = setup_mcp_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "tool": "search_approved_facts",
        "arguments": {"query": "latency"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/mcp/tools/call",
            json=payload,
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["result"]["total_matches"] >= 1
    assert any("latency" in f["statement"].lower() for f in data["result"]["facts"])


@pytest.mark.asyncio
async def test_mcp_audit_text_tool(setup_mcp_test_env):
    """Verifies invoking pre-publication compliance audit via MCP."""
    env = setup_mcp_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "tool": "audit_text",
        "arguments": {
            "title": "Agent Generated Landing Page",
            "text": "Get the cheap cloud tier now. Certified latency is below 15ms across 99% of global regions.",
        },
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/mcp/tools/call",
            json=payload,
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "readiness_score" in data["result"]
    assert "findings" in data["result"]
    assert data["audit_event_id"] is not None


@pytest.mark.asyncio
async def test_mcp_safety_gate_denies_approval(setup_mcp_test_env):
    """Verifies that MCP clients cannot grant final approval or bypass human reviewers."""
    env = setup_mcp_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "tool": "approve_submission",
        "arguments": {"submission_id": "test-sub-123"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/mcp/tools/call",
            json=payload,
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Suggest, Never Override" in data["error"]


@pytest.mark.asyncio
async def test_mcp_workspace_isolation(setup_mcp_test_env):
    """Verifies that an unauthorized caller cannot invoke MCP tools for another workspace."""
    env = setup_mcp_test_env
    ws_id = env["workspace"].id

    outsider = User(
        email="outsider_agent@external.com",
        hashed_password="Password123",
        full_name="Outsider Agent",
        is_active=True,
    )
    await outsider.insert()
    token = create_access_token(subject=outsider.id, email=outsider.email)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/mcp/tools/call",
            json={"tool": "get_brand_rules", "arguments": {}},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert res.status_code == 403
