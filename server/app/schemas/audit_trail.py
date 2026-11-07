"""Pydantic v2 schemas for Audit Trail, Cryptographic Verification, and Security Posture."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.services.audit_verifier import AuditChainVerificationReport


class AuditEventItem(BaseModel):
    id: str
    workspace_id: str
    actor_user_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    metadata_json: Optional[Dict[str, Any]] = None
    previous_hash: Optional[str] = None
    event_hash: str
    created_at: datetime


class AuditTrailResponse(BaseModel):
    items: List[AuditEventItem]
    total: int
    skip: int
    limit: int
    has_more: bool


class PrivacyGateSecurityStats(BaseModel):
    total_submissions_scrubbed: int
    total_pii_entities_redacted: int
    total_confidential_terms_masked: int


class GovernanceSecurityStats(BaseModel):
    total_audits_performed: int
    total_approvals_granted: int
    total_certificates_minted: int
    total_exceptions_requested: int
    total_exceptions_approved: int


class RbacPostureStats(BaseModel):
    total_members: int
    governance_admins_count: int
    reviewers_count: int
    creators_count: int
    tenant_isolation_enforced: bool = True


class SecurityPostureResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    ledger_integrity: AuditChainVerificationReport
    privacy_gate_stats: PrivacyGateSecurityStats
    governance_stats: GovernanceSecurityStats
    rbac_posture: RbacPostureStats
    assessed_at: datetime
