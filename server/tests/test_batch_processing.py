"""Unit and integration tests for Campaign Batch Auditing and Executive Governance Reports."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.documents import User, Workspace, Membership, BatchAudit, AuditEvent
from app.core.security import create_access_token


@pytest.fixture
async def setup_batch_test_env():
    """Sets up workspace, admin user, and auth headers for batch testing."""
    ws = Workspace(name="Batch Testing Workspace", slug="batch-test-ws")
    await ws.insert()

    user = User(
        email="batch_admin@veribrand.io",
        hashed_password="TestPasswordHash123",
        full_name="Batch Governance Admin",
        is_active=True,
    )
    await user.insert()

    membership = Membership(
        workspace_id=ws.id,
        user_id=user.id,
        role="GOVERNANCE_ADMIN",
    )
    await membership.insert()

    token = create_access_token(subject=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    return {"workspace": ws, "user": user, "headers": headers}


@pytest.mark.asyncio
async def test_create_and_run_batch_audit(setup_batch_test_env):
    """Verifies creating a multi-item batch audit and executing deterministic + AI verification."""
    env = setup_batch_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "title": "Q3 Global Omni-Channel Campaign",
        "campaign_tag": "q3-omni-launch",
        "items": [
            {
                "title": "Press Release Announcement",
                "content": "Acme Global announces breakthrough efficiency. Contact john.doe@acme.com for details.",
                "file_name": "press_release.txt",
            },
            {
                "title": "Social Media Promotional Copy",
                "content": "Supercharge your business with 100% guaranteed zero downtime and flawless reliability.",
                "file_name": "social_post.txt",
            },
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            f"/api/v1/workspaces/{ws_id}/batches",
            json=payload,
            params={"auto_run": True},
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Q3 Global Omni-Channel Campaign"
    assert data["campaign_tag"] == "q3-omni-launch"
    assert data["total_items"] == 2
    assert data["completed_items"] == 2
    assert data["status"] == "COMPLETED"
    assert len(data["items"]) == 2
    assert "aggregate_score" in data
    assert "campaign_rating" in data


@pytest.mark.asyncio
async def test_list_and_get_batch_details(setup_batch_test_env):
    """Verifies listing workspace batches and retrieving detailed item breakdown."""
    env = setup_batch_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "title": "Product Brochure Batch",
        "campaign_tag": "brochures-2026",
        "items": [
            {
                "title": "Enterprise Solution Overview",
                "content": "Discover how Acme Global empowers scalable cloud workflows worldwide.",
            }
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/batches",
            json=payload,
            params={"auto_run": True},
            headers=headers,
        )
        batch_id = create_res.json()["id"]

        # List batches
        list_res = await ac.get(
            f"/api/v1/workspaces/{ws_id}/batches",
            headers=headers,
        )
        assert list_res.status_code == 200
        batch_list = list_res.json()
        assert any(b["id"] == batch_id for b in batch_list)

        # Get batch details
        detail_res = await ac.get(
            f"/api/v1/workspaces/{ws_id}/batches/{batch_id}",
            headers=headers,
        )
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == batch_id
        assert detail["title"] == "Product Brochure Batch"
        assert len(detail["items"]) == 1


@pytest.mark.asyncio
async def test_export_executive_batch_report(setup_batch_test_env):
    """Verifies generating structured executive governance export."""
    env = setup_batch_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "title": "Executive Summary Batch",
        "campaign_tag": "exec-report-test",
        "items": [
            {
                "title": "Annual Shareholder Letter",
                "content": "Acme Global delivered record governance compliance in 2026.",
            }
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/batches",
            json=payload,
            headers=headers,
        )
        batch_id = create_res.json()["id"]

        export_res = await ac.get(
            f"/api/v1/workspaces/{ws_id}/batches/{batch_id}/export",
            headers=headers,
        )

    assert export_res.status_code == 200
    export_data = export_res.json()
    assert export_data["batch_id"] == batch_id
    assert export_data["title"] == "Executive Summary Batch"
    assert "aggregate_score" in export_data
    assert "campaign_rating" in export_data
    assert len(export_data["items"]) == 1


@pytest.mark.asyncio
async def test_batch_audit_trail_chained(setup_batch_test_env):
    """Verifies batch lifecycle operations generate tamper-evident chained audit events."""
    env = setup_batch_test_env
    ws_id = env["workspace"].id
    headers = env["headers"]

    payload = {
        "title": "Audit Trail Validation Batch",
        "items": [
            {
                "title": "Compliance Policy Statement",
                "content": "All marketing materials must satisfy pre-publication standards.",
            }
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            f"/api/v1/workspaces/{ws_id}/batches",
            json=payload,
            params={"auto_run": True},
            headers=headers,
        )
        batch_id = create_res.json()["id"]

    events = await AuditEvent.find(
        AuditEvent.workspace_id == ws_id,
        AuditEvent.entity_id == batch_id,
    ).to_list()

    actions = [e.action for e in events]
    assert "BATCH_CREATED" in actions
    assert "BATCH_AUDITED" in actions
    for ev in events:
        assert ev.event_hash is not None


@pytest.mark.asyncio
async def test_batch_workspace_isolation(setup_batch_test_env):
    """Verifies that users from another workspace cannot access or trigger batch runs."""
    env = setup_batch_test_env
    ws_id = env["workspace"].id

    # Create an outsider user not in this workspace
    outsider = User(
        email="outsider@rivalbrand.com",
        hashed_password="HashPassword123",
        full_name="Outsider User",
        is_active=True,
    )
    await outsider.insert()

    outsider_token = create_access_token(subject=outsider.id, email=outsider.email)
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/workspaces/{ws_id}/batches",
            headers=outsider_headers,
        )
        assert res.status_code == 403
