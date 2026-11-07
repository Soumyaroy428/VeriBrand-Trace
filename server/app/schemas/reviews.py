"""Pydantic schemas for Reviewer queue, comments, sign-off approvals, compliance certificates, and governance analytics."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewCommentCreateRequest(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=2000, description="Reviewer feedback or comment")
    revision_id: Optional[str] = Field(None, description="Target revision ID; defaults to latest")
    anchor_location: Optional[Dict[str, Any]] = Field(None, description="Optional target anchor, e.g. line or finding ID")


class ReviewCommentResponse(BaseModel):
    id: str
    submission_id: str
    revision_id: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    comment_text: str
    anchor_location: Optional[Dict[str, Any]] = None
    created_at: datetime


class ExceptionDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$", description="Reviewer decision on exception")
    decision_note: Optional[str] = Field(None, max_length=1000, description="Reviewer justification or notes")


class ApprovalRequest(BaseModel):
    decision_notes: Optional[str] = Field(None, max_length=2000, description="Optional sign-off approval notes")


class RejectionRequest(BaseModel):
    decision_notes: str = Field(..., min_length=3, max_length=2000, description="Required justification for rejection")


class ComplianceCertificateResponse(BaseModel):
    id: str
    certificate_number: str
    submission_id: str
    approval_id: str
    workspace_id: str
    certificate_hash: str
    issued_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None


class ApprovalResponse(BaseModel):
    id: str
    submission_id: str
    revision_id: str
    decided_by: str
    decided_by_email: Optional[str] = None
    decision: str
    decision_notes: Optional[str] = None
    readiness_score_at_approval: int
    created_at: datetime
    certificate: Optional[ComplianceCertificateResponse] = None


class ReviewQueueItem(BaseModel):
    submission_id: str
    title: str
    creator_id: str
    creator_email: Optional[str] = None
    format: str
    current_status: str
    revision_count: int
    latest_revision_id: str
    readiness_score: Optional[int] = None
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    pending_exceptions: int = 0
    comments_count: int = 0
    updated_at: datetime


class ReviewQueueResponse(BaseModel):
    workspace_id: str
    total_count: int
    items: List[ReviewQueueItem]


class GovernanceInsightsResponse(BaseModel):
    workspace_id: str
    total_submissions: int
    total_approved: int
    total_rejected: int
    total_pending: int
    approval_rate: float
    avg_readiness_score: float
    total_exceptions_requested: int
    total_exceptions_approved: int
    total_exceptions_rejected: int
    category_breakdown: Dict[str, int]
    top_violated_rules: List[Dict[str, Any]]
    severity_breakdown: Dict[str, int]


class CertificateVerificationResponse(BaseModel):
    valid: bool
    certificate_number: str
    certificate_hash: str
    computed_hash: str
    submission_title: str
    submission_id: str
    workspace_name: str
    readiness_score: int
    decided_by_email: str
    issued_at: datetime
    tamper_evident_verified: bool
