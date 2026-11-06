"""Comprehensive test suite for Checkpoint 3: Authentication and Workspace RBAC."""

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
from app.models.documents import User, Workspace, Membership, AuditEvent
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes mock MongoDB database before each test."""
    mock_client = AsyncMongoMockClient()
    await init_db(client=mock_client, db_name="test_auth_db")
    yield
    await close_db()


@pytest_asyncio.fixture
async def client():
    """Provides an async HTTP client connected to the FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_register_success(client: httpx.AsyncClient):
    """Verify that a new user can register successfully."""
    payload = {
        "email": "sarah.creator@acme.com",
        "password": "SecurePassword123!",
        "full_name": "Sarah Creator",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "sarah.creator@acme.com"
    assert data["full_name"] == "Sarah Creator"
    assert "id" in data
    assert data["is_active"] is True

    # Verify user exists in database and password is encrypted
    user = await User.get(data["id"])
    assert user is not None
    assert user.hashed_password != "SecurePassword123!"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: httpx.AsyncClient):
    """Verify duplicate email registration is rejected with 409 Conflict."""
    payload = {
        "email": "duplicate@acme.com",
        "password": "SecurePassword123!",
        "full_name": "Original User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"]["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_success(client: httpx.AsyncClient):
    """Verify successful login returns valid JWT token and user info."""
    user = User(
        email="john.reviewer@acme.com",
        hashed_password=get_password_hash("ValidSecret2026!"),
        full_name="John Reviewer",
        is_active=True,
    )
    await user.insert()

    login_payload = {
        "email": "john.reviewer@acme.com",
        "password": "ValidSecret2026!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "john.reviewer@acme.com"
    assert data["user"]["full_name"] == "John Reviewer"


@pytest.mark.asyncio
async def test_login_invalid_password(client: httpx.AsyncClient):
    """Verify invalid password returns 401 Unauthorized."""
    user = User(
        email="target@acme.com",
        hashed_password=get_password_hash("CorrectPassword"),
        full_name="Target User",
        is_active=True,
    )
    await user.insert()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "target@acme.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_disabled_account(client: httpx.AsyncClient):
    """Verify inactive/disabled accounts cannot log in."""
    user = User(
        email="disabled@acme.com",
        hashed_password=get_password_hash("CorrectPassword"),
        full_name="Disabled User",
        is_active=False,
    )
    await user.insert()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "disabled@acme.com", "password": "CorrectPassword"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "ACCOUNT_DISABLED"


@pytest.mark.asyncio
async def test_get_current_user_profile(client: httpx.AsyncClient):
    """Verify /api/v1/auth/me returns authenticated user profile and workspace roles."""
    user = User(
        email="eva.admin@acme.com",
        hashed_password=get_password_hash("AdminPass123"),
        full_name="Eva Admin",
        is_active=True,
    )
    await user.insert()

    workspace = Workspace(name="Acme Europe", slug="acme-eu", status="ACTIVE")
    await workspace.insert()

    membership = Membership(workspace_id=workspace.id, user_id=user.id, role="GOVERNANCE_ADMIN")
    await membership.insert()

    token = create_access_token(subject=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "eva.admin@acme.com"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["workspace_slug"] == "acme-eu"
    assert data["workspaces"][0]["role"] == "GOVERNANCE_ADMIN"


@pytest.mark.asyncio
async def test_auth_me_invalid_token(client: httpx.AsyncClient):
    """Verify that an invalid or expired token is rejected with 401."""
    headers = {"Authorization": "Bearer invalid.jwt.token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_create_workspace_assigns_governance_admin(client: httpx.AsyncClient):
    """Verify creating a workspace automatically assigns GOVERNANCE_ADMIN role and logs audit event."""
    user = User(
        email="founder@acme.com",
        hashed_password=get_password_hash("Founder123!"),
        full_name="Founder User",
        is_active=True,
    )
    await user.insert()

    token = create_access_token(subject=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    ws_payload = {"name": "Acme North America", "slug": "acme-na"}
    response = await client.post("/api/v1/workspaces", json=ws_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme North America"
    assert data["slug"] == "acme-na"
    assert data["current_user_role"] == "GOVERNANCE_ADMIN"

    # Verify audit event was logged
    audit_event = await AuditEvent.find_one(
        AuditEvent.workspace_id == data["id"],
        AuditEvent.action == "WORKSPACE_CREATED",
    )
    assert audit_event is not None
    assert audit_event.actor_user_id == user.id
    assert audit_event.event_hash is not None


@pytest.mark.asyncio
async def test_rbac_add_member_permissions(client: httpx.AsyncClient):
    """Verify GOVERNANCE_ADMIN can add members, but CREATOR role cannot."""
    # Create workspace owner (GOVERNANCE_ADMIN)
    admin_user = User(email="admin@acme.com", hashed_password=get_password_hash("pass"), full_name="Admin", is_active=True)
    await admin_user.insert()

    # Create a regular creator
    creator_user = User(email="creator@acme.com", hashed_password=get_password_hash("pass"), full_name="Creator", is_active=True)
    await creator_user.insert()

    # Create target new member to invite
    new_user = User(email="newbie@acme.com", hashed_password=get_password_hash("pass"), full_name="Newbie", is_active=True)
    await new_user.insert()

    # Workspace
    workspace = Workspace(name="Test Org", slug="test-org", status="ACTIVE")
    await workspace.insert()

    # Assign Admin & Creator memberships
    await Membership(workspace_id=workspace.id, user_id=admin_user.id, role="GOVERNANCE_ADMIN").insert()
    await Membership(workspace_id=workspace.id, user_id=creator_user.id, role="CREATOR").insert()

    # Attempt 1: Creator tries to add a member -> Should fail with 403 INSUFFICIENT_PERMISSIONS
    creator_token = create_access_token(subject=creator_user.id, email=creator_user.email)
    creator_headers = {"Authorization": f"Bearer {creator_token}"}
    member_payload = {"user_email": "newbie@acme.com", "role": "REVIEWER"}

    resp1 = await client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json=member_payload,
        headers=creator_headers,
    )
    assert resp1.status_code == 403
    assert resp1.json()["detail"]["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # Attempt 2: Admin adds the member -> Should succeed with 201 Created
    admin_token = create_access_token(subject=admin_user.id, email=admin_user.email)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp2 = await client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json=member_payload,
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    assert resp2.json()["user_email"] == "newbie@acme.com"
    assert resp2.json()["role"] == "REVIEWER"


@pytest.mark.asyncio
async def test_cross_workspace_isolation_denied(client: httpx.AsyncClient):
    """Verify that a user who does not belong to a workspace receives 403 Forbidden."""
    outsider = User(email="outsider@rival.com", hashed_password=get_password_hash("pass"), full_name="Outsider", is_active=True)
    await outsider.insert()

    workspace = Workspace(name="Secret Lab", slug="secret-lab", status="ACTIVE")
    await workspace.insert()

    token = create_access_token(subject=outsider.id, email=outsider.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get(f"/api/v1/workspaces/{workspace.id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_logout_endpoint(client: httpx.AsyncClient):
    """Verify /api/v1/auth/logout succeeds for authenticated users."""
    user = User(email="logout.user@acme.com", hashed_password=get_password_hash("pass"), full_name="Logout User", is_active=True)
    await user.insert()

    token = create_access_token(subject=user.id, email=user.email)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
