"""Comprehensive automated test suite for MongoDB Beanie models & Checkpoint 2."""

import sys
import os
import pytest
import pytest_asyncio
import mongomock
from mongomock_motor import AsyncMongoMockClient

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
from app.core.seed import seed_database
from app.models.documents import (
    User,
    Workspace,
    Membership,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    FindingEvidence,
    AuditEvent,
    ALL_MODELS,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes in-memory mock MongoDB before each test."""
    mock_client = AsyncMongoMockClient()
    await init_db(client=mock_client, db_name="test_veribrand")
    yield
    await close_db()


@pytest.mark.asyncio
async def test_models_registration():
    """Verify that all 19 Beanie document models are properly registered."""
    assert len(ALL_MODELS) == 19
    for model in ALL_MODELS:
        assert hasattr(model, "id")
        assert hasattr(model, "Settings")


@pytest.mark.asyncio
async def test_workspace_and_user_crud():
    """Verify CRUD operations for Workspace and User entities."""
    user = User(
        email="test_creator@acme.com",
        hashed_password="mock_hashed_secret",
        full_name="Alice Creator",
        is_active=True,
    )
    await user.insert()
    assert user.id is not None

    workspace = Workspace(
        name="Beta Brand Ltd",
        slug="beta-brand",
        status="ACTIVE",
    )
    await workspace.insert()
    assert workspace.id is not None

    membership = Membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role="CREATOR",
    )
    await membership.insert()

    # Query verification
    retrieved_user = await User.find_one(User.email == "test_creator@acme.com")
    assert retrieved_user is not None
    assert retrieved_user.full_name == "Alice Creator"

    retrieved_membership = await Membership.find_one(
        Membership.workspace_id == workspace.id,
        Membership.user_id == user.id,
    )
    assert retrieved_membership is not None
    assert retrieved_membership.role == "CREATOR"


@pytest.mark.asyncio
async def test_workspace_isolation():
    """Verify strict tenant isolation between different brand workspaces."""
    # Create Workspace A
    ws_a = Workspace(name="Workspace Alpha", slug="ws-alpha")
    await ws_a.insert()

    # Create Workspace B
    ws_b = Workspace(name="Workspace Beta", slug="ws-beta")
    await ws_b.insert()

    # Insert Fact in Workspace A
    fact_a = ApprovedFact(
        workspace_id=ws_a.id,
        fact_key="revenue_2026",
        statement="Alpha generated 50M revenue.",
        created_by="user_alpha",
    )
    await fact_a.insert()

    # Insert Fact in Workspace B
    fact_b = ApprovedFact(
        workspace_id=ws_b.id,
        fact_key="revenue_2026",
        statement="Beta generated 10M revenue.",
        created_by="user_beta",
    )
    await fact_b.insert()

    # Verify that querying Workspace A only retrieves Workspace A's facts
    alpha_facts = await ApprovedFact.find(ApprovedFact.workspace_id == ws_a.id).to_list()
    assert len(alpha_facts) == 1
    assert alpha_facts[0].statement == "Alpha generated 50M revenue."

    # Verify that querying Workspace B only retrieves Workspace B's facts
    beta_facts = await ApprovedFact.find(ApprovedFact.workspace_id == ws_b.id).to_list()
    assert len(beta_facts) == 1
    assert beta_facts[0].statement == "Beta generated 10M revenue."


@pytest.mark.asyncio
async def test_submission_and_revision_immutability():
    """Verify Submission lifecycle and revision versioning."""
    ws = Workspace(name="Acme", slug="acme")
    await ws.insert()

    submission = Submission(
        workspace_id=ws.id,
        created_by="user_123",
        title="Q3 Press Release",
        input_type="TEXT",
        status="DRAFT",
    )
    await submission.insert()

    # Create original Revision 1
    rev_1 = SubmissionRevision(
        submission_id=submission.id,
        revision_number=1,
        content_hash="hash_rev1_original",
        extracted_text="Original unverified text with claim X.",
        created_by="user_123",
    )
    await rev_1.insert()

    # Create edited Revision 2
    rev_2 = SubmissionRevision(
        submission_id=submission.id,
        revision_number=2,
        content_hash="hash_rev2_edited",
        extracted_text="Revised verified text with approved fact X.",
        created_by="user_123",
    )
    await rev_2.insert()

    revisions = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("revision_number").to_list()

    assert len(revisions) == 2
    assert revisions[0].revision_number == 1
    assert revisions[1].revision_number == 2
    assert revisions[0].content_hash != revisions[1].content_hash


@pytest.mark.asyncio
async def test_audit_event_tamper_evident_hash_chain():
    """Verify SHA-256 tamper-evident hash chaining on AuditEvent."""
    ws = Workspace(name="Security Brand", slug="sec-brand")
    await ws.insert()

    # Event 1 (Genesis event)
    time_1 = "2026-11-06T12:00:00Z"
    hash_1 = AuditEvent.calculate_hash(
        workspace_id=ws.id,
        actor_user_id="admin_1",
        entity_type="SUBMISSION",
        entity_id="sub_100",
        action="SUBMISSION_CREATED",
        metadata_json={"title": "Security Report"},
        previous_hash=None,
        created_at_iso=time_1,
    )
    event_1 = AuditEvent(
        workspace_id=ws.id,
        actor_user_id="admin_1",
        entity_type="SUBMISSION",
        entity_id="sub_100",
        action="SUBMISSION_CREATED",
        metadata_json={"title": "Security Report"},
        previous_hash=None,
        event_hash=hash_1,
    )
    await event_1.insert()

    # Event 2 (Chained to Event 1)
    time_2 = "2026-11-06T12:05:00Z"
    hash_2 = AuditEvent.calculate_hash(
        workspace_id=ws.id,
        actor_user_id="reviewer_1",
        entity_type="SUBMISSION",
        entity_id="sub_100",
        action="AUDIT_APPROVED",
        metadata_json={"score": 98},
        previous_hash=hash_1,
        created_at_iso=time_2,
    )
    event_2 = AuditEvent(
        workspace_id=ws.id,
        actor_user_id="reviewer_1",
        entity_type="SUBMISSION",
        entity_id="sub_100",
        action="AUDIT_APPROVED",
        metadata_json={"score": 98},
        previous_hash=hash_1,
        event_hash=hash_2,
    )
    await event_2.insert()

    # Validation: Verify that Event 2 correctly references Event 1
    events = await AuditEvent.find(AuditEvent.workspace_id == ws.id).to_list()
    assert len(events) == 2
    assert events[1].previous_hash == events[0].event_hash

    # Tamper detection: Altering metadata changes the expected hash
    tampered_hash = AuditEvent.calculate_hash(
        workspace_id=ws.id,
        actor_user_id="admin_1",
        entity_type="SUBMISSION",
        entity_id="sub_100",
        action="SUBMISSION_CREATED",
        metadata_json={"title": "TAMPERED REPORT"},
        previous_hash=None,
        created_at_iso=time_1,
    )
    assert tampered_hash != hash_1


@pytest.mark.asyncio
async def test_seed_database_execution():
    """Verify that development seed script populates all entities properly."""
    result = await seed_database()
    assert "workspace_id" in result
    assert result["workspace_slug"] == "acme-global"

    # Verify seeded workspace
    ws = await Workspace.find_one(Workspace.slug == "acme-global")
    assert ws is not None

    # Verify seeded users
    users = await User.find_all().to_list()
    assert len(users) >= 3

    # Verify seeded approved facts
    facts = await ApprovedFact.find(ApprovedFact.workspace_id == ws.id).to_list()
    assert len(facts) >= 3

    # Verify seeded terminology rules
    terms = await TerminologyRule.find(TerminologyRule.workspace_id == ws.id).to_list()
    assert len(terms) >= 3

    # Verify seeded visual rules
    visuals = await VisualRule.find(VisualRule.workspace_id == ws.id).to_list()
    assert len(visuals) >= 2

    # Verify genesis audit event
    genesis = await AuditEvent.find_one(
        AuditEvent.workspace_id == ws.id,
        AuditEvent.action == "WORKSPACE_SEEDED",
    )
    assert genesis is not None
    assert genesis.event_hash == result["genesis_hash"]
