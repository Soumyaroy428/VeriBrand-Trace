"""Pydantic schemas for Batch Audit processing and campaign executive reports."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class BatchItemCreate(BaseModel):
    """Single content item inside a batch submission."""
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    file_name: Optional[str] = None


class BatchCreateRequest(BaseModel):
    """Payload to create and queue a new campaign batch audit."""
    title: str = Field(..., min_length=2, max_length=200)
    campaign_tag: Optional[str] = Field(None, max_length=100)
    items: List[BatchItemCreate] = Field(..., min_length=1, max_length=25)


class BatchItemSummary(BaseModel):
    """Summary of a single audited submission in a batch."""
    submission_id: str
    title: str
    status: str
    readiness_score: float = 0.0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    total_findings: int = 0


class BatchAuditResponse(BaseModel):
    """Detailed batch audit response with aggregated metrics."""
    id: str
    workspace_id: str
    title: str
    campaign_tag: Optional[str] = None
    created_by: str
    status: str
    total_items: int
    completed_items: int
    aggregate_score: float
    critical_violations: int
    warning_violations: int
    info_violations: int
    campaign_rating: str
    created_at: datetime
    updated_at: datetime
    items: List[BatchItemSummary] = []


class BatchExportReport(BaseModel):
    """Executive governance report export for a campaign batch."""
    batch_id: str
    workspace_id: str
    title: str
    campaign_tag: Optional[str] = None
    aggregate_score: float
    campaign_rating: str
    total_items: int
    completed_items: int
    critical_violations: int
    warning_violations: int
    generated_at: str
    items: List[Dict[str, Any]]
