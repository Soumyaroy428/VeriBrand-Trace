"""MongoDB Document models using Beanie ODM and Pydantic v2.

Defines all 18 entities specified in DATABASE.md:
- Multi-tenancy: Every brand entity is strictly scoped to a workspace_id.
- Security: AuditEvent implements cryptographic SHA-256 hash chaining.
- Performance: Compound and unique indexes on high-frequency query paths.
"""

import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field
from pymongo import IndexModel, ASCENDING
from beanie import Document
from app.models.base import generate_uuid, utc_now


# 1. User Account
class User(Document):
    id: str = Field(default_factory=generate_uuid)
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
        ]


# 2. Brand Workspace (Tenant)
class Workspace(Document):
    id: str = Field(default_factory=generate_uuid)
    name: str
    slug: str
    status: str = "ACTIVE"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "workspaces"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True),
        ]


# 3. Workspace Membership & Role
class Membership(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    user_id: str
    role: str = "CREATOR"  # CREATOR, REVIEWER, GOVERNANCE_ADMIN
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "memberships"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("user_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING)]),
        ]


# 4. Guideline Document
class GuidelineDocument(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    title: str
    file_name: str
    storage_key: str
    content_hash: str
    version: int = 1
    status: str = "ACTIVE"
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "guideline_documents"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("status", ASCENDING)]),
        ]


# 5. Guideline Chunk (Vector Evidence Passages)
class GuidelineChunk(Document):
    id: str = Field(default_factory=generate_uuid)
    document_id: str
    workspace_id: str
    chunk_index: int
    content: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    token_count: int = 0
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "guideline_chunks"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("document_id", ASCENDING)]),
        ]


# 6. Approved Fact Registry
class ApprovedFact(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    fact_key: str
    statement: str
    value_json: Optional[Dict[str, Any]] = None
    source_reference: Optional[str] = None
    status: str = "ACTIVE"
    version: int = 1
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "approved_facts"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("fact_key", ASCENDING)]),
            IndexModel([("workspace_id", ASCENDING), ("status", ASCENDING)]),
        ]


# 7. Terminology Rule
class TerminologyRule(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    term: str
    rule_type: str = "BANNED"  # BANNED, PREFERRED, REPLACEMENT
    replacement: Optional[str] = None
    case_sensitive: bool = False
    whole_word: bool = True
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    guideline_reference: Optional[str] = None
    active: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "terminology_rules"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("active", ASCENDING)]),
        ]


# 8. Visual Standards Rule
class VisualRule(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    rule_type: str  # COLOR_PALETTE, LOGO_CLEARSPACE, CONTRAST_RATIO
    rule_config: Dict[str, Any]
    severity: str = "HIGH"
    source_reference: Optional[str] = None
    active: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "visual_rules"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("rule_type", ASCENDING)]),
        ]


# 9. Brand Assets
class BrandAsset(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    name: str
    asset_type: str  # LOGO, ICON, COLOR_SWATCH, DOCUMENT
    storage_key: str
    file_hash: str
    metadata_json: Optional[Dict[str, Any]] = None
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "brand_assets"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("asset_type", ASCENDING)]),
        ]


# 10. Submission (Content Audit Request)
class Submission(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    created_by: str
    title: str
    input_type: str  # TEXT, DOCX, PDF, IMAGE_PNG, IMAGE_JPG
    status: str = "DRAFT"  # DRAFT, PROCESSING, NEEDS_CHANGES, PENDING_REVIEW, APPROVED, REJECTED, FAILED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "submissions"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
        ]


# 11. Submission Revision (Immutable Version History)
class SubmissionRevision(Document):
    id: str = Field(default_factory=generate_uuid)
    submission_id: str
    revision_number: int = 1
    storage_key: Optional[str] = None
    content_hash: str
    extracted_text: Optional[str] = None
    sanitized_text: Optional[str] = None
    privacy_gate_metadata: Optional[Dict[str, Any]] = None
    raw_content: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "submission_revisions"
        indexes = [
            IndexModel([("submission_id", ASCENDING), ("revision_number", ASCENDING)], unique=True),
        ]


# 12. Audit Run
class AuditRun(Document):
    id: str = Field(default_factory=generate_uuid)
    submission_id: str
    revision_id: str
    status: str = "QUEUED"  # QUEUED, PROCESSING, COMPLETED, PARTIAL, FAILED
    deterministic_status: str = "PENDING"
    ai_status: str = "PENDING"
    readiness_score: Optional[int] = None
    model_identifier: Optional[str] = None
    rule_set_version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "audit_runs"
        indexes = [
            IndexModel([("submission_id", ASCENDING), ("revision_id", ASCENDING)]),
        ]


# 13. Finding (Violation / Observation)
class Finding(Document):
    id: str = Field(default_factory=generate_uuid)
    audit_run_id: str
    category: str  # TERMINOLOGY, FACT_CHECK, COLOR_COMPLIANCE, CONTRAST, CLAIM_ACCURACY, TONE_MESSAGING
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    source_engine: str  # DETERMINISTIC, RAG_AI
    title: str
    description: str
    location: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    suggestion: Optional[Dict[str, Any]] = None
    status: str = "OPEN"  # OPEN, ACCEPTED, EDITED, EXCEPTION_REQUESTED, OVERRIDDEN, RESOLVED
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "findings"
        indexes = [
            IndexModel([("audit_run_id", ASCENDING), ("severity", ASCENDING)]),
        ]


# 14. Finding Evidence Passage
class FindingEvidence(Document):
    id: str = Field(default_factory=generate_uuid)
    finding_id: str
    source_type: str  # RULE, APPROVED_FACT, GUIDELINE_CHUNK
    source_id: Optional[str] = None
    source_version: int = 1
    quote: str
    location: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "finding_evidence"
        indexes = [
            IndexModel([("finding_id", ASCENDING)]),
        ]


# 15. Exception Request
class ExceptionRequest(Document):
    id: str = Field(default_factory=generate_uuid)
    finding_id: str
    submission_id: str
    requested_by: str
    reason: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    decided_by: Optional[str] = None
    decision_note: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    decided_at: Optional[datetime] = None

    class Settings:
        name = "exceptions"
        indexes = [
            IndexModel([("submission_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("finding_id", ASCENDING)]),
        ]


# 16. Reviewer Comment
class ReviewComment(Document):
    id: str = Field(default_factory=generate_uuid)
    submission_id: str
    revision_id: str
    user_id: str
    comment_text: str
    anchor_location: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "review_comments"
        indexes = [
            IndexModel([("submission_id", ASCENDING), ("revision_id", ASCENDING)]),
        ]


# 17. Final Review Approval / Sign-off
class Approval(Document):
    id: str = Field(default_factory=generate_uuid)
    submission_id: str
    revision_id: str
    decided_by: str
    decision: str  # APPROVED, REJECTED
    decision_notes: Optional[str] = None
    readiness_score_at_approval: int
    created_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "approvals"
        indexes = [
            IndexModel([("submission_id", ASCENDING)]),
        ]


# 18. Tamper-Evident Append-Only Audit Event
class AuditEvent(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    actor_user_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    metadata_json: Optional[Dict[str, Any]] = None
    previous_hash: Optional[str] = None
    event_hash: str
    created_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def calculate_hash(
        cls,
        workspace_id: str,
        actor_user_id: Optional[str],
        entity_type: str,
        entity_id: str,
        action: str,
        metadata_json: Optional[Dict[str, Any]],
        previous_hash: Optional[str],
        created_at_iso: str,
    ) -> str:
        """Computes deterministic SHA-256 event hash chaining."""
        payload = {
            "workspace_id": workspace_id,
            "actor_user_id": actor_user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "metadata_json": metadata_json,
            "previous_hash": previous_hash,
            "created_at": created_at_iso,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    class Settings:
        name = "audit_events"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", ASCENDING)]),
            IndexModel([("entity_type", ASCENDING), ("entity_id", ASCENDING)]),
        ]


# 19. Compliance Certificate
class ComplianceCertificate(Document):
    id: str = Field(default_factory=generate_uuid)
    approval_id: str
    submission_id: str
    workspace_id: str
    certificate_number: str
    certificate_hash: str
    issued_at: datetime = Field(default_factory=utc_now)
    metadata_json: Optional[Dict[str, Any]] = None

    class Settings:
        name = "compliance_certificates"
        indexes = [
            IndexModel([("certificate_number", ASCENDING)], unique=True),
            IndexModel([("submission_id", ASCENDING)]),
        ]


# 20. Batch Audit Run (Campaign Multi-Item Processing)
class BatchAudit(Document):
    id: str = Field(default_factory=generate_uuid)
    workspace_id: str
    title: str
    campaign_tag: Optional[str] = None
    created_by: str
    status: str = "PENDING"  # PENDING, PROCESSING, COMPLETED, FAILED
    submission_ids: List[str] = Field(default_factory=list)
    total_items: int = 0
    completed_items: int = 0
    aggregate_score: float = 0.0
    critical_violations: int = 0
    warning_violations: int = 0
    info_violations: int = 0
    campaign_rating: str = "PENDING_AUDIT"  # CAMPAIGN_READY, REQUIRES_REMEDIATION, CRITICAL_RISK
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "batch_audits"
        indexes = [
            IndexModel([("workspace_id", ASCENDING), ("created_at", ASCENDING)]),
            IndexModel([("campaign_tag", ASCENDING)]),
        ]


# All Document models registered for Beanie initialization
ALL_MODELS = [
    User,
    Workspace,
    Membership,
    GuidelineDocument,
    GuidelineChunk,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    BrandAsset,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    FindingEvidence,
    ExceptionRequest,
    ReviewComment,
    Approval,
    AuditEvent,
    ComplianceCertificate,
    BatchAudit,
]

