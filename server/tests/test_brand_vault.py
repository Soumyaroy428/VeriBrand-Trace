"""Comprehensive automated test suite for Checkpoint 4: Brand Vault."""

import sys
import os
import pytest
import pytest_asyncio
import mongomock
from mongomock_motor import AsyncMongoMockClient
import httpx

# Ensure server root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch mongomock Database.list_collection_names to only accept supported kwargs
_orig_list_colls = mongomock.database.Database.list_collection_names
def _patched_list_colls(self, *args, **kwargs):
    valid_kwargs = {}
    if "filter" in kwargs:
        valid_kwargs["filter"] = kwargs["filter"]
    return _orig_list_colls(self, *args, **valid_kwargs)
mongomock.database.Database.list_collection_names = _patched_list_colls

from app.core.database import init_db, close_db
from app.core.security import get_password_hash, create_access_token
from app.models.documents import (
    User,
    Workspace,
    Membership,
    GuidelineDocument,
    GuidelineChunk,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    BrandAsset,
    AuditEvent,
)
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes in-memory mock MongoDB before each test."""
    mock_client = AsyncMongoMockClient()
    await init_db(client=mock_client, db_name="test_vault_db")
    yield
    await close_db()


@pytest_asyncio.fixture
async def client():
    """Provides an async HTTP client connected to the FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def setup_workspace():
    """Provisions a test workspace with an Admin, a Creator, and an Outsider."""
    admin = User(email="carol.admin@acme.com", hashed_password=get_password_hash("pass"), full_name="Carol Admin", is_active=True)
    await admin.insert()

    creator = User(email="alice.creator@acme.com", hashed_password=get_password_hash("pass"), full_name="Alice Creator", is_active=True)
    await creator.insert()

    outsider = User(email="eve.outsider@rival.com", hashed_password=get_password_hash("pass"), full_name="Eve Outsider", is_active=True)
    await outsider.insert()

    ws = Workspace(name="Acme Vault Org", slug="acme-vault-org", status="ACTIVE")
    await ws.insert()

    await Membership(workspace_id=ws.id, user_id=admin.id, role="GOVERNANCE_ADMIN").insert()
    await Membership(workspace_id=ws.id, user_id=creator.id, role="CREATOR").insert()

    admin_token = create_access_token(subject=admin.id, email=admin.email)
    creator_token = create_access_token(subject=creator.id, email=creator.email)
    outsider_token = create_access_token(subject=outsider.id, email=outsider.email)

    return {
        "workspace": ws,
        "admin": admin,
        "creator": creator,
        "outsider": outsider,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "creator_headers": {"Authorization": f"Bearer {creator_token}"},
        "outsider_headers": {"Authorization": f"Bearer {outsider_token}"},
    }


@pytest.mark.asyncio
async def test_guideline_ingestion_and_chunking(client: httpx.AsyncClient, setup_workspace):
    """Verify guideline document ingestion, SHA-256 hashing, and automated paragraph chunking."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]
    creator_headers = setup_workspace["creator_headers"]

    raw_guidelines = (
        "1. Brand Voice and Tone\n\n"
        "VeriBrand communicates with clarity, humility, and technical rigor. We avoid hyperbole.\n\n"
        "2. Visual Clearspace\n\n"
        "Maintain a minimum 24px buffer zone around the primary mark on all digital surfaces."
    )

    payload = {
        "title": "Acme Brand Guidelines 2026",
        "file_name": "brand-2026.md",
        "storage_key": "guidelines/brand-2026.md",
        "content": raw_guidelines,
    }

    # Admin ingests guideline
    res = await client.post(f"/api/v1/workspaces/{ws.id}/guidelines", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Acme Brand Guidelines 2026"
    assert data["chunk_count"] == 4  # 4 paragraph blocks
    assert data["version"] == 1
    assert data["content_hash"] is not None
    guideline_id = data["id"]

    # Creator reads guideline chunks
    chunks_res = await client.get(f"/api/v1/workspaces/{ws.id}/guidelines/{guideline_id}/chunks", headers=creator_headers)
    assert chunks_res.status_code == 200
    chunks = chunks_res.json()
    assert len(chunks) == 4
    assert chunks[0]["chunk_index"] == 0
    assert "Brand Voice and Tone" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_approved_facts_crud_and_versioning(client: httpx.AsyncClient, setup_workspace):
    """Verify approved facts creation, version incrementing on update, and revocation."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]

    # 1. Create Fact
    fact_payload = {
        "fact_key": "q3_revenue",
        "statement": "Acme generated $120M ARR in Q3 2026.",
        "source_reference": "Q3 10-Q Filing, pg 14",
    }
    create_res = await client.post(f"/api/v1/workspaces/{ws.id}/facts", json=fact_payload, headers=admin_headers)
    assert create_res.status_code == 201
    fact_data = create_res.json()
    assert fact_data["fact_key"] == "q3_revenue"
    assert fact_data["version"] == 1
    assert fact_data["status"] == "ACTIVE"
    fact_id = fact_data["id"]

    # 2. Update Fact (statement revised -> version must become 2)
    update_payload = {
        "statement": "Acme generated $122.5M audited ARR in Q3 2026.",
        "source_reference": "Q3 Audited Restatement, pg 2",
    }
    update_res = await client.put(f"/api/v1/workspaces/{ws.id}/facts/{fact_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["version"] == 2
    assert "122.5M" in updated_data["statement"]

    # 3. List Facts
    list_res = await client.get(f"/api/v1/workspaces/{ws.id}/facts?status_filter=ACTIVE", headers=admin_headers)
    assert list_res.status_code == 200
    facts_list = list_res.json()
    assert len(facts_list) == 1
    assert facts_list[0]["version"] == 2

    # 4. Revoke Fact
    del_res = await client.delete(f"/api/v1/workspaces/{ws.id}/facts/{fact_id}", headers=admin_headers)
    assert del_res.status_code == 200

    # Fact should now be REVOKED
    revoked_fact = await ApprovedFact.get(fact_id)
    assert revoked_fact.status == "REVOKED"


@pytest.mark.asyncio
async def test_terminology_rules_crud(client: httpx.AsyncClient, setup_workspace):
    """Verify terminology rule creation, filtering, and deactivation."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]

    payload = {
        "term": "unbreakable security",
        "rule_type": "BANNED",
        "replacement": "industry-standard protection",
        "guideline_reference": "Absolute security claims violate FTC compliance standards.",
        "case_sensitive": False,
        "whole_word": True,
        "severity": "CRITICAL",
    }
    res = await client.post(f"/api/v1/workspaces/{ws.id}/terminology-rules", json=payload, headers=admin_headers)
    assert res.status_code == 201
    rule_data = res.json()
    assert rule_data["term"] == "unbreakable security"
    assert rule_data["severity"] == "CRITICAL"
    assert rule_data["active"] is True
    rule_id = rule_data["id"]

    # List rules
    list_res = await client.get(f"/api/v1/workspaces/{ws.id}/terminology-rules", headers=admin_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Deactivate rule
    del_res = await client.delete(f"/api/v1/workspaces/{ws.id}/terminology-rules/{rule_id}", headers=admin_headers)
    assert del_res.status_code == 200

    rule = await TerminologyRule.get(rule_id)
    assert rule.active is False


@pytest.mark.asyncio
async def test_visual_rules_and_assets(client: httpx.AsyncClient, setup_workspace):
    """Verify visual rules (hex, Delta-E, contrast) and digital brand assets."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]

    # 1. Create Visual Standard
    vis_payload = {
        "rule_type": "COLOR_PALETTE",
        "name": "Acme Brand Deep Navy",
        "color_hex": "#0F172A",
        "tolerance_delta_e": 2.5,
        "min_contrast_ratio": 7.0,
        "severity": "HIGH",
    }
    vis_res = await client.post(f"/api/v1/workspaces/{ws.id}/visual-rules", json=vis_payload, headers=admin_headers)
    assert vis_res.status_code == 201
    vis_data = vis_res.json()
    assert vis_data["rule_config"]["color_hex"] == "#0F172A"
    assert vis_data["rule_config"]["min_contrast_ratio"] == 7.0

    # 2. Register Brand Asset
    asset_payload = {
        "name": "Acme Monochrome Vector Mark",
        "asset_type": "LOGO",
        "storage_key": "logos/mark-mono.svg",
    }
    asset_res = await client.post(f"/api/v1/workspaces/{ws.id}/assets", json=asset_payload, headers=admin_headers)
    assert asset_res.status_code == 201
    assert asset_res.json()["name"] == "Acme Monochrome Vector Mark"


@pytest.mark.asyncio
async def test_brand_vault_summary(client: httpx.AsyncClient, setup_workspace):
    """Verify aggregate count summary across all Brand Vault registries."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]

    # Seed 1 Fact, 1 Term, 1 Visual Rule
    await client.post(f"/api/v1/workspaces/{ws.id}/facts", json={"fact_key": "k1", "statement": "Fact One 2026"}, headers=admin_headers)
    await client.post(f"/api/v1/workspaces/{ws.id}/terminology-rules", json={"term": "badword", "rule_type": "BANNED"}, headers=admin_headers)
    await client.post(f"/api/v1/workspaces/{ws.id}/visual-rules", json={"rule_type": "COLOR_PALETTE", "name": "Teal", "color_hex": "#0D9488"}, headers=admin_headers)

    summary_res = await client.get(f"/api/v1/workspaces/{ws.id}/brand-vault/summary", headers=admin_headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["approved_facts_count"] == 1
    assert summary["terminology_rules_count"] == 1
    assert summary["visual_rules_count"] == 1


@pytest.mark.asyncio
async def test_brand_vault_rbac_enforcement(client: httpx.AsyncClient, setup_workspace):
    """Verify that Creators cannot write to Brand Vault, but can read; outsiders cannot read or write."""
    ws = setup_workspace["workspace"]
    creator_headers = setup_workspace["creator_headers"]
    outsider_headers = setup_workspace["outsider_headers"]

    fact_payload = {"fact_key": "creator_fact", "statement": "Unauthorized creator fact attempt"}

    # Attempt 1: Creator tries to create a fact -> 403 INSUFFICIENT_PERMISSIONS
    res1 = await client.post(f"/api/v1/workspaces/{ws.id}/facts", json=fact_payload, headers=creator_headers)
    assert res1.status_code == 403
    assert res1.json()["detail"]["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # Attempt 2: Creator reads facts -> 200 OK
    res2 = await client.get(f"/api/v1/workspaces/{ws.id}/facts", headers=creator_headers)
    assert res2.status_code == 200

    # Attempt 3: Outsider tries to read facts -> 403 FORBIDDEN
    res3 = await client.get(f"/api/v1/workspaces/{ws.id}/facts", headers=outsider_headers)
    assert res3.status_code == 403
    assert res3.json()["detail"]["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_brand_vault_workspace_isolation(client: httpx.AsyncClient, setup_workspace):
    """Verify strict tenant isolation: facts in Workspace A are not visible in Workspace B."""
    ws_a = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]
    admin_user = setup_workspace["admin"]

    # Create second workspace for same admin
    ws_b = Workspace(name="Second Org", slug="second-org", status="ACTIVE")
    await ws_b.insert()
    await Membership(workspace_id=ws_b.id, user_id=admin_user.id, role="GOVERNANCE_ADMIN").insert()

    # Add fact to Workspace A
    await client.post(f"/api/v1/workspaces/{ws_a.id}/facts", json={"fact_key": "org_a_fact", "statement": "Exclusive Org A Fact"}, headers=admin_headers)

    # Query Workspace B -> should be empty
    res_b = await client.get(f"/api/v1/workspaces/{ws_b.id}/facts", headers=admin_headers)
    assert res_b.status_code == 200
    assert len(res_b.json()) == 0


@pytest.mark.asyncio
async def test_brand_vault_cryptographic_audit_chaining(client: httpx.AsyncClient, setup_workspace):
    """Verify that Brand Vault operations record chained SHA-256 AuditEvents."""
    ws = setup_workspace["workspace"]
    admin_headers = setup_workspace["admin_headers"]

    # Action 1: Create Fact
    res1 = await client.post(f"/api/v1/workspaces/{ws.id}/facts", json={"fact_key": "audit_fact", "statement": "Audited Fact Statement"}, headers=admin_headers)
    assert res1.status_code == 201

    # Action 2: Create Terminology Rule
    res2 = await client.post(f"/api/v1/workspaces/{ws.id}/terminology-rules", json={"term": "banned_word", "rule_type": "BANNED"}, headers=admin_headers)
    assert res2.status_code == 201

    # Check AuditEvent chain
    events = await AuditEvent.find(AuditEvent.workspace_id == ws.id).sort("created_at").to_list()
    assert len(events) >= 2
    latest = events[-1]
    second_latest = events[-2]

    # Verify cryptographic previous_hash linkage
    assert latest.previous_hash == second_latest.event_hash
