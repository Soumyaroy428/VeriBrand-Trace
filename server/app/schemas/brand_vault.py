"""Pydantic v2 validation schemas for Brand Vault: guidelines, facts, terminology, and visual rules."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# Guidelines & Chunks
# ==========================================

class GuidelineDocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=200)
    file_name: str = Field("guidelines.md", max_length=200)
    storage_key: str = Field("guidelines/master.md", max_length=300)
    content: Optional[str] = Field(None, description="Full raw markdown/text content if ingested directly")


class GuidelineChunkResponse(BaseModel):
    id: str
    document_id: str
    workspace_id: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    token_count: int
    created_at: datetime


class GuidelineDocumentResponse(BaseModel):
    id: str
    workspace_id: str
    title: str
    file_name: str
    storage_key: str
    content_hash: str
    version: int
    status: str
    chunk_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime


# ==========================================
# Approved Facts
# ==========================================

class ApprovedFactCreateRequest(BaseModel):
    fact_key: str = Field(..., min_length=2, max_length=100)
    statement: str = Field(..., min_length=5, max_length=1000)
    value_json: Optional[Dict[str, Any]] = None
    source_reference: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class ApprovedFactUpdateRequest(BaseModel):
    statement: Optional[str] = Field(None, min_length=5, max_length=1000)
    value_json: Optional[Dict[str, Any]] = None
    source_reference: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(ACTIVE|SUPERSEDED|REVOKED)$")
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class ApprovedFactResponse(BaseModel):
    id: str
    workspace_id: str
    fact_key: str
    statement: str
    value_json: Optional[Dict[str, Any]] = None
    version: int
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: str
    source_reference: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


# ==========================================
# Terminology Rules
# ==========================================

class TerminologyRuleCreateRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=150)
    rule_type: str = Field("BANNED", pattern="^(BANNED|PREFERRED|REPLACEMENT)$")
    replacement: Optional[str] = Field(None, max_length=150)
    guideline_reference: Optional[str] = Field(None, max_length=500)
    case_sensitive: bool = False
    whole_word: bool = True
    severity: str = Field("HIGH", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)$")


class TerminologyRuleUpdateRequest(BaseModel):
    term: Optional[str] = Field(None, min_length=1, max_length=150)
    rule_type: Optional[str] = Field(None, pattern="^(BANNED|PREFERRED|REPLACEMENT)$")
    replacement: Optional[str] = None
    guideline_reference: Optional[str] = None
    case_sensitive: Optional[bool] = None
    whole_word: Optional[bool] = None
    severity: Optional[str] = Field(None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)$")
    active: Optional[bool] = None


class TerminologyRuleResponse(BaseModel):
    id: str
    workspace_id: str
    term: str
    rule_type: str
    replacement: Optional[str] = None
    case_sensitive: bool
    whole_word: bool
    severity: str
    guideline_reference: Optional[str] = None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


# ==========================================
# Visual Rules
# ==========================================

class VisualRuleCreateRequest(BaseModel):
    rule_type: str = Field("COLOR_PALETTE", pattern="^(COLOR_PALETTE|LOGO_CLEARSPACE|CONTRAST_RATIO)$")
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    color_hex: Optional[str] = Field(None, pattern="^#(?:[0-9a-fA-F]{3}){1,2}$")
    tolerance_delta_e: Optional[float] = Field(2.0, ge=0.0, le=50.0)
    min_contrast_ratio: Optional[float] = Field(4.5, ge=1.0, le=21.0)
    severity: str = Field("HIGH", pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)$")
    source_reference: Optional[str] = None
    rule_config: Optional[Dict[str, Any]] = None


class VisualRuleUpdateRequest(BaseModel):
    rule_type: Optional[str] = Field(None, pattern="^(COLOR_PALETTE|LOGO_CLEARSPACE|CONTRAST_RATIO)$")
    name: Optional[str] = None
    color_hex: Optional[str] = Field(None, pattern="^#(?:[0-9a-fA-F]{3}){1,2}$")
    tolerance_delta_e: Optional[float] = Field(None, ge=0.0, le=50.0)
    min_contrast_ratio: Optional[float] = Field(None, ge=1.0, le=21.0)
    severity: Optional[str] = Field(None, pattern="^(CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)$")
    source_reference: Optional[str] = None
    active: Optional[bool] = None
    rule_config: Optional[Dict[str, Any]] = None


class VisualRuleResponse(BaseModel):
    id: str
    workspace_id: str
    rule_type: str
    rule_config: Dict[str, Any]
    severity: str
    source_reference: Optional[str] = None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


# ==========================================
# Brand Assets
# ==========================================

class BrandAssetCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    asset_type: str = Field("LOGO", pattern="^(LOGO|ICON|COLOR_SWATCH|DOCUMENT)$")
    storage_key: str = Field(...)
    file_hash: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class BrandAssetResponse(BaseModel):
    id: str
    workspace_id: str
    name: str
    asset_type: str
    storage_key: str
    file_hash: str
    metadata_json: Optional[Dict[str, Any]] = None
    active: bool
    created_at: datetime


# ==========================================
# Brand Vault Overall Summary
# ==========================================

class BrandVaultSummaryResponse(BaseModel):
    workspace_id: str
    guidelines_count: int
    approved_facts_count: int
    terminology_rules_count: int
    visual_rules_count: int
    assets_count: int
