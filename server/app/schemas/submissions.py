"""Pydantic schemas for Submissions, Revisions, and Privacy Gate reports."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PiiFindingSchema(BaseModel):
    type: str
    snippet_masked: str
    mask_applied: str
    start: int
    end: int


class ConfidentialTermMaskedSchema(BaseModel):
    term: str
    token: str
    occurrences: int


class PrivacyGateReportSchema(BaseModel):
    status: str  # PASSED, SANITIZED, BLOCKED
    pii_count: int = 0
    terms_count: int = 0
    pii_detected: List[PiiFindingSchema] = []
    confidential_terms_masked: List[ConfidentialTermMaskedSchema] = []
    original_char_count: int = 0
    sanitized_char_count: int = 0


class ContentSubmissionCreate(BaseModel):
    """Schema for direct text submission via JSON body."""
    title: str = Field(..., min_length=2, max_length=200)
    text_content: str = Field(..., min_length=1)
    input_type: str = "TEXT"
    confidential_terms: Optional[List[str]] = Field(default_factory=list)


class SubmissionRevisionCreate(BaseModel):
    """Schema for adding an updated revision to an existing submission."""
    raw_content: str = Field(..., min_length=1)
    confidential_terms: Optional[List[str]] = Field(default_factory=list)


class SubmissionRevisionResponse(BaseModel):
    id: str
    submission_id: str
    revision_number: int
    storage_key: Optional[str] = None
    content_hash: str
    extracted_text: Optional[str] = None
    sanitized_text: Optional[str] = None
    privacy_gate_metadata: Optional[Dict[str, Any]] = None
    created_by: str
    created_at: datetime


class SubmissionResponse(BaseModel):
    id: str
    workspace_id: str
    created_by: str
    title: str
    input_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    latest_revision: Optional[SubmissionRevisionResponse] = None


class SubmissionListResponse(BaseModel):
    submissions: List[SubmissionResponse]
    total: int


class SubmissionDetailResponse(BaseModel):
    submission: SubmissionResponse
    revisions: List[SubmissionRevisionResponse]
