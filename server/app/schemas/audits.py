"""Pydantic schemas for Audits, Findings, and Compliance Evidence."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class FindingEvidenceResponse(BaseModel):
    id: str
    finding_id: str
    source_type: str
    source_id: Optional[str] = None
    source_version: int = 1
    quote: str
    location: Optional[Dict[str, Any]] = None
    created_at: datetime


class FindingResponse(BaseModel):
    id: str
    audit_run_id: str
    category: str
    severity: str
    source_engine: str
    title: str
    description: str
    location: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    suggestion: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    evidence_list: List[FindingEvidenceResponse] = []


class AuditRunResponse(BaseModel):
    id: str
    submission_id: str
    revision_id: str
    status: str
    deterministic_status: str
    ai_status: str
    readiness_score: Optional[int] = None
    model_identifier: Optional[str] = None
    rule_set_version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    created_at: datetime
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0


class AuditRunWithFindingsResponse(BaseModel):
    audit_run: AuditRunResponse
    findings: List[FindingResponse]


# --- Checkpoint 8: Diff & Exception Schemas ---

class ExceptionCreateRequest(BaseModel):
    reason: str


class ExceptionResponse(BaseModel):
    id: str
    finding_id: str
    submission_id: str
    requested_by: str
    reason: str
    status: str
    created_at: datetime


class ApplySuggestionRequest(BaseModel):
    finding_id: str


class DiffChunk(BaseModel):
    type: str  # "equal", "delete", "insert"
    text: str


class DiffLine(BaseModel):
    line_number_orig: Optional[int] = None
    line_number_rev: Optional[int] = None
    type: str  # "equal", "modified", "delete", "insert"
    original_text: Optional[str] = None
    revised_text: Optional[str] = None


class DiffResponse(BaseModel):
    submission_id: str
    from_revision_number: int
    to_revision_number: int
    original_text: str
    revised_text: str
    chunks: List[DiffChunk]
    lines: List[DiffLine]
    stats: Dict[str, int]

