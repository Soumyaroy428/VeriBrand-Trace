"""API routes for Audit Trail ledger exploration, cryptographic chain verification,
and enterprise security posture telemetry.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.models.documents import (
    AuditEvent,
    AuditRun,
    Approval,
    ComplianceCertificate,
    ExceptionRequest,
    Membership,
    Submission,
    SubmissionRevision,
    User,
    Workspace,
)
from app.models.base import utc_now
from app.services.audit_verifier import (
    verify_workspace_audit_chain,
    AuditChainVerificationReport,
)
from app.schemas.audit_trail import (
    AuditEventItem,
    AuditTrailResponse,
    PrivacyGateSecurityStats,
    GovernanceSecurityStats,
    RbacPostureStats,
    SecurityPostureResponse,
)

router = APIRouter()


async def check_workspace_access(
    workspace_id: str,
    user: User,
    allowed_roles: Optional[List[str]] = None,
) -> Membership:
    """Helper to enforce workspace-scoped RBAC permissions."""
    if user.is_superuser:
        return Membership(workspace_id=workspace_id, user_id=user.id, role="GOVERNANCE_ADMIN")

    membership = await Membership.find_one(
        Membership.workspace_id == workspace_id,
        Membership.user_id == user.id,
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have access to this workspace",
        )

    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{membership.role}' lacks permission for this security resource",
        )
    return membership


@router.get(
    "/{workspace_id}/audit-trail",
    response_model=AuditTrailResponse,
    summary="List paginated, filterable tamper-evident audit events for a brand workspace",
)
async def get_workspace_audit_trail(
    workspace_id: str,
    action: Optional[str] = Query(None, description="Filter by event action"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    actor_user_id: Optional[str] = Query(None, description="Filter by actor user ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    await check_workspace_access(
        workspace_id,
        current_user,
        allowed_roles=["GOVERNANCE_ADMIN", "REVIEWER", "CREATOR"],
    )

    # Build query criteria list
    criteria = [AuditEvent.workspace_id == workspace_id]
    if action:
        criteria.append(AuditEvent.action == action)
    if entity_type:
        criteria.append(AuditEvent.entity_type == entity_type)
    if actor_user_id:
        criteria.append(AuditEvent.actor_user_id == actor_user_id)

    total = await AuditEvent.find(*criteria).count()

    events = await AuditEvent.find(*criteria).sort("-created_at").skip(skip).limit(limit).to_list()

    # Pre-fetch user profiles for human-friendly display
    user_ids = {e.actor_user_id for e in events if e.actor_user_id}
    users_cache: Dict[str, User] = {}
    for uid in user_ids:
        u = await User.get(uid)
        if u:
            users_cache[uid] = u

    items: List[AuditEventItem] = []
    for ev in events:
        actor = users_cache.get(ev.actor_user_id) if ev.actor_user_id else None
        items.append(
            AuditEventItem(
                id=ev.id,
                workspace_id=ev.workspace_id,
                actor_user_id=ev.actor_user_id,
                actor_name=actor.full_name if actor else None,
                actor_email=actor.email if actor else None,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                action=ev.action,
                metadata_json=ev.metadata_json,
                previous_hash=ev.previous_hash,
                event_hash=ev.event_hash,
                created_at=ev.created_at,
            )
        )

    return AuditTrailResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=(skip + len(items) < total),
    )


@router.get(
    "/{workspace_id}/audit-trail/verify",
    response_model=AuditChainVerificationReport,
    summary="Cryptographically verify unbroken SHA-256 hash chaining across all workspace audit events",
)
async def verify_audit_ledger(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    await check_workspace_access(
        workspace_id,
        current_user,
        allowed_roles=["GOVERNANCE_ADMIN", "REVIEWER"],
    )

    workspace = await Workspace.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return await verify_workspace_audit_chain(workspace_id)


@router.get(
    "/{workspace_id}/security/posture",
    response_model=SecurityPostureResponse,
    summary="Comprehensive security, privacy gate, and cryptographic posture assessment",
)
async def get_security_posture(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    await check_workspace_access(
        workspace_id,
        current_user,
        allowed_roles=["GOVERNANCE_ADMIN", "REVIEWER"],
    )

    workspace = await Workspace.get(workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # 1. Cryptographic ledger integrity check
    ledger_integrity = await verify_workspace_audit_chain(workspace_id)

    # 2. Privacy gate statistics
    submissions = await Submission.find(Submission.workspace_id == workspace_id).to_list()
    sub_ids = [s.id for s in submissions]
    scrubbed_count = 0
    pii_redacted_total = 0
    terms_masked_total = 0

    if sub_ids:
        all_revisions = await SubmissionRevision.find().to_list()
        revisions = [r for r in all_revisions if r.submission_id in sub_ids]
        for rev in revisions:
            meta = rev.privacy_gate_metadata or {}
            if meta.get("scrubbed", False):
                scrubbed_count += 1
            pii_entities = meta.get("pii_entities", [])
            terms_masked = meta.get("confidential_terms_masked", [])
            pii_redacted_total += len(pii_entities)
            terms_masked_total += len(terms_masked)

    # 3. Governance Statistics
    sub_id_set = set(sub_ids)
    all_audit_runs = await AuditRun.find().to_list()
    audit_runs_count = sum(1 for ar in all_audit_runs if ar.submission_id in sub_id_set)

    all_approvals = await Approval.find().to_list()
    approvals_count = sum(1 for ap in all_approvals if ap.submission_id in sub_id_set)

    certificates_count = await ComplianceCertificate.find(ComplianceCertificate.workspace_id == workspace_id).count()

    all_exceptions = await ExceptionRequest.find().to_list()
    exceptions = [ex for ex in all_exceptions if ex.submission_id in sub_id_set]
    exceptions_total = len(exceptions)
    exceptions_approved = sum(1 for ex in exceptions if ex.status == "APPROVED")

    # 4. RBAC Posture
    members = await Membership.find(Membership.workspace_id == workspace_id).to_list()
    admin_count = sum(1 for m in members if m.role == "GOVERNANCE_ADMIN")
    reviewer_count = sum(1 for m in members if m.role == "REVIEWER")
    creator_count = sum(1 for m in members if m.role == "CREATOR")

    return SecurityPostureResponse(
        workspace_id=workspace_id,
        workspace_name=workspace.name,
        ledger_integrity=ledger_integrity,
        privacy_gate_stats=PrivacyGateSecurityStats(
            total_submissions_scrubbed=scrubbed_count,
            total_pii_entities_redacted=pii_redacted_total,
            total_confidential_terms_masked=terms_masked_total,
        ),
        governance_stats=GovernanceSecurityStats(
            total_audits_performed=audit_runs_count,
            total_approvals_granted=approvals_count,
            total_certificates_minted=certificates_count,
            total_exceptions_requested=exceptions_total,
            total_exceptions_approved=exceptions_approved,
        ),
        rbac_posture=RbacPostureStats(
            total_members=len(members),
            governance_admins_count=admin_count,
            reviewers_count=reviewer_count,
            creators_count=creator_count,
            tenant_isolation_enforced=True,
        ),
        assessed_at=utc_now(),
    )
