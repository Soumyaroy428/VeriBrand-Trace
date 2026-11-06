"""Brand Vault API endpoints: Guidelines, Approved Facts, Terminology Rules, Visual Standards, Assets."""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.core.dependencies import get_current_user, require_workspace_role
from app.models.documents import (
    User,
    Membership,
    GuidelineDocument,
    GuidelineChunk,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    BrandAsset,
    AuditEvent,
)
from app.schemas.brand_vault import (
    GuidelineDocumentCreateRequest,
    GuidelineDocumentResponse,
    GuidelineChunkResponse,
    ApprovedFactCreateRequest,
    ApprovedFactUpdateRequest,
    ApprovedFactResponse,
    TerminologyRuleCreateRequest,
    TerminologyRuleUpdateRequest,
    TerminologyRuleResponse,
    VisualRuleCreateRequest,
    VisualRuleUpdateRequest,
    VisualRuleResponse,
    BrandAssetCreateRequest,
    BrandAssetResponse,
    BrandVaultSummaryResponse,
)

router = APIRouter()


async def record_audit_event(
    workspace_id: str,
    actor_user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    metadata_json: dict,
) -> AuditEvent:
    """Helper to append an immutable, SHA-256 chained audit event."""
    created_at_now = datetime.now(timezone.utc)
    created_at_iso = created_at_now.isoformat()

    last_event = await AuditEvent.find(
        AuditEvent.workspace_id == workspace_id
    ).sort("-created_at").first_or_none()
    previous_hash = last_event.event_hash if last_event else None

    event_hash = AuditEvent.calculate_hash(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata_json=metadata_json,
        previous_hash=previous_hash,
        created_at_iso=created_at_iso,
    )

    event = AuditEvent(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata_json=metadata_json,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at_now,
    )
    await event.insert()
    return event


# ==========================================
# Brand Vault Summary
# ==========================================

@router.get("/workspaces/{workspace_id}/brand-vault/summary", response_model=BrandVaultSummaryResponse)
async def get_brand_vault_summary(
    workspace_id: str,
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """Retrieve aggregate counts across all Brand Vault registries."""
    g_count = await GuidelineDocument.find(GuidelineDocument.workspace_id == workspace_id).count()
    f_count = await ApprovedFact.find(ApprovedFact.workspace_id == workspace_id, ApprovedFact.status == "ACTIVE").count()
    t_count = await TerminologyRule.find(TerminologyRule.workspace_id == workspace_id, TerminologyRule.active == True).count()
    v_count = await VisualRule.find(VisualRule.workspace_id == workspace_id, VisualRule.active == True).count()
    a_count = await BrandAsset.find(BrandAsset.workspace_id == workspace_id, BrandAsset.active == True).count()

    return BrandVaultSummaryResponse(
        workspace_id=workspace_id,
        guidelines_count=g_count,
        approved_facts_count=f_count,
        terminology_rules_count=t_count,
        visual_rules_count=v_count,
        assets_count=a_count,
    )


# ==========================================
# Guidelines
# ==========================================

@router.get("/workspaces/{workspace_id}/guidelines", response_model=List[GuidelineDocumentResponse])
async def list_guidelines(
    workspace_id: str,
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """List all guideline documents for the workspace."""
    docs = await GuidelineDocument.find(GuidelineDocument.workspace_id == workspace_id).to_list()
    res = []
    for doc in docs:
        c_count = await GuidelineChunk.find(GuidelineChunk.document_id == doc.id).count()
        res.append(
            GuidelineDocumentResponse(
                id=doc.id,
                workspace_id=doc.workspace_id,
                title=doc.title,
                file_name=doc.file_name,
                storage_key=doc.storage_key,
                content_hash=doc.content_hash,
                version=doc.version,
                status=doc.status,
                chunk_count=c_count,
                created_by=doc.created_by,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )
    return res


@router.post("/workspaces/{workspace_id}/guidelines", response_model=GuidelineDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_guideline(
    workspace_id: str,
    request: GuidelineDocumentCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Ingest a new brand guideline document. Restricted to GOVERNANCE_ADMIN."""
    raw_content = request.content or ""
    content_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

    doc = GuidelineDocument(
        workspace_id=workspace_id,
        title=request.title,
        file_name=request.file_name,
        storage_key=request.storage_key,
        content_hash=content_hash,
        version=1,
        status="ACTIVE",
        created_by=current_user.id,
    )
    await doc.insert()

    # Automatically chunk if text content is supplied
    chunk_count = 0
    if request.content:
        paragraphs = [p.strip() for p in request.content.split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            chunk = GuidelineChunk(
                document_id=doc.id,
                workspace_id=workspace_id,
                chunk_index=idx,
                section_title=f"Section {idx + 1}",
                content=para,
                token_count=len(para.split()),
            )
            await chunk.insert()
            chunk_count += 1

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="GUIDELINE_DOCUMENT",
        entity_id=doc.id,
        action="GUIDELINE_INGESTED",
        metadata_json={"title": doc.title, "version": doc.version, "chunks": chunk_count},
    )

    return GuidelineDocumentResponse(
        id=doc.id,
        workspace_id=doc.workspace_id,
        title=doc.title,
        file_name=doc.file_name,
        storage_key=doc.storage_key,
        content_hash=doc.content_hash,
        version=doc.version,
        status=doc.status,
        chunk_count=chunk_count,
        created_by=doc.created_by,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get("/workspaces/{workspace_id}/guidelines/{guideline_id}/chunks", response_model=List[GuidelineChunkResponse])
async def list_guideline_chunks(
    workspace_id: str,
    guideline_id: str,
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """Retrieve chunk evidence passages for a specific guideline."""
    chunks = await GuidelineChunk.find(
        GuidelineChunk.workspace_id == workspace_id,
        GuidelineChunk.document_id == guideline_id,
    ).sort("chunk_index").to_list()

    return [
        GuidelineChunkResponse(
            id=c.id,
            document_id=c.document_id,
            workspace_id=c.workspace_id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section_title=c.section_title,
            content=c.content,
            token_count=c.token_count,
            created_at=c.created_at,
        )
        for c in chunks
    ]


# ==========================================
# Approved Facts
# ==========================================

@router.get("/workspaces/{workspace_id}/facts", response_model=List[ApprovedFactResponse])
async def list_approved_facts(
    workspace_id: str,
    status_filter: Optional[str] = Query(None, description="Optional filter by status: ACTIVE, SUPERSEDED, REVOKED"),
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """List approved facts registry for the workspace."""
    query = [ApprovedFact.workspace_id == workspace_id]
    if status_filter:
        query.append(ApprovedFact.status == status_filter)

    facts = await ApprovedFact.find(*query).sort("-created_at").to_list()
    return [
        ApprovedFactResponse(
            id=f.id,
            workspace_id=f.workspace_id,
            fact_key=f.fact_key,
            statement=f.statement,
            value_json=f.value_json,
            version=f.version,
            valid_from=f.valid_from,
            valid_until=f.valid_until,
            status=f.status,
            source_reference=f.source_reference,
            created_by=f.created_by,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in facts
    ]


@router.post("/workspaces/{workspace_id}/facts", response_model=ApprovedFactResponse, status_code=status.HTTP_201_CREATED)
async def create_approved_fact(
    workspace_id: str,
    request: ApprovedFactCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Add an approved fact to the registry. Restricted to GOVERNANCE_ADMIN."""
    existing = await ApprovedFact.find_one(
        ApprovedFact.workspace_id == workspace_id,
        ApprovedFact.fact_key == request.fact_key,
        ApprovedFact.status == "ACTIVE",
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "FACT_KEY_EXISTS", "message": f"Active fact with key '{request.fact_key}' already exists"}},
        )

    fact = ApprovedFact(
        workspace_id=workspace_id,
        fact_key=request.fact_key,
        statement=request.statement,
        value_json=request.value_json,
        source_reference=request.source_reference,
        version=1,
        valid_from=request.valid_from or datetime.now(timezone.utc),
        valid_until=request.valid_until,
        status="ACTIVE",
        created_by=current_user.id,
    )
    await fact.insert()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="APPROVED_FACT",
        entity_id=fact.id,
        action="FACT_CREATED",
        metadata_json={"fact_key": fact.fact_key, "version": fact.version},
    )

    return ApprovedFactResponse(
        id=fact.id,
        workspace_id=fact.workspace_id,
        fact_key=fact.fact_key,
        statement=fact.statement,
        value_json=fact.value_json,
        version=fact.version,
        valid_from=fact.valid_from,
        valid_until=fact.valid_until,
        status=fact.status,
        source_reference=fact.source_reference,
        created_by=fact.created_by,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


@router.put("/workspaces/{workspace_id}/facts/{fact_id}", response_model=ApprovedFactResponse)
async def update_approved_fact(
    workspace_id: str,
    fact_id: str,
    request: ApprovedFactUpdateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Update an existing approved fact (increments version). Restricted to GOVERNANCE_ADMIN."""
    fact = await ApprovedFact.find_one(
        ApprovedFact.id == fact_id,
        ApprovedFact.workspace_id == workspace_id,
    )
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "FACT_NOT_FOUND", "message": "Fact not found"}},
        )

    if request.statement is not None:
        fact.statement = request.statement
    if request.value_json is not None:
        fact.value_json = request.value_json
    if request.valid_from is not None:
        fact.valid_from = request.valid_from
    if request.valid_until is not None:
        fact.valid_until = request.valid_until
    if request.status is not None:
        fact.status = request.status
    if request.source_reference is not None:
        fact.source_reference = request.source_reference

    fact.version += 1
    fact.updated_at = datetime.now(timezone.utc)
    await fact.save()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="APPROVED_FACT",
        entity_id=fact.id,
        action="FACT_UPDATED",
        metadata_json={"fact_key": fact.fact_key, "new_version": fact.version},
    )

    return ApprovedFactResponse(
        id=fact.id,
        workspace_id=fact.workspace_id,
        fact_key=fact.fact_key,
        statement=fact.statement,
        value_json=fact.value_json,
        version=fact.version,
        valid_from=fact.valid_from,
        valid_until=fact.valid_until,
        status=fact.status,
        source_reference=fact.source_reference,
        created_by=fact.created_by,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


@router.delete("/workspaces/{workspace_id}/facts/{fact_id}", status_code=status.HTTP_200_OK)
async def delete_approved_fact(
    workspace_id: str,
    fact_id: str,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Revoke an approved fact. Restricted to GOVERNANCE_ADMIN."""
    fact = await ApprovedFact.find_one(
        ApprovedFact.id == fact_id,
        ApprovedFact.workspace_id == workspace_id,
    )
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "FACT_NOT_FOUND", "message": "Fact not found"}},
        )

    fact.status = "REVOKED"
    fact.updated_at = datetime.now(timezone.utc)
    await fact.save()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="APPROVED_FACT",
        entity_id=fact.id,
        action="FACT_REVOKED",
        metadata_json={"fact_key": fact.fact_key},
    )

    return {"status": "success", "message": f"Fact '{fact.fact_key}' revoked successfully"}


# ==========================================
# Terminology Rules
# ==========================================

@router.get("/workspaces/{workspace_id}/terminology-rules", response_model=List[TerminologyRuleResponse])
async def list_terminology_rules(
    workspace_id: str,
    active_only: bool = Query(True),
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """List terminology rules for the workspace."""
    query = [TerminologyRule.workspace_id == workspace_id]
    if active_only:
        query.append(TerminologyRule.active == True)

    rules = await TerminologyRule.find(*query).sort("-created_at").to_list()
    return [
        TerminologyRuleResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            term=r.term,
            rule_type=r.rule_type,
            replacement=r.replacement,
            case_sensitive=r.case_sensitive,
            whole_word=r.whole_word,
            severity=r.severity,
            guideline_reference=r.guideline_reference,
            active=r.active,
            version=r.version,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.post("/workspaces/{workspace_id}/terminology-rules", response_model=TerminologyRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_terminology_rule(
    workspace_id: str,
    request: TerminologyRuleCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Add a new terminology compliance rule. Restricted to GOVERNANCE_ADMIN."""
    rule = TerminologyRule(
        workspace_id=workspace_id,
        term=request.term,
        rule_type=request.rule_type,
        replacement=request.replacement,
        case_sensitive=request.case_sensitive,
        whole_word=request.whole_word,
        severity=request.severity,
        guideline_reference=request.guideline_reference,
        active=True,
        version=1,
    )
    await rule.insert()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="TERMINOLOGY_RULE",
        entity_id=rule.id,
        action="TERMINOLOGY_RULE_CREATED",
        metadata_json={"term": rule.term, "rule_type": rule.rule_type, "severity": rule.severity},
    )

    return TerminologyRuleResponse(
        id=rule.id,
        workspace_id=rule.workspace_id,
        term=rule.term,
        rule_type=rule.rule_type,
        replacement=rule.replacement,
        case_sensitive=rule.case_sensitive,
        whole_word=rule.whole_word,
        severity=rule.severity,
        guideline_reference=rule.guideline_reference,
        active=rule.active,
        version=rule.version,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/workspaces/{workspace_id}/terminology-rules/{rule_id}", status_code=status.HTTP_200_OK)
async def delete_terminology_rule(
    workspace_id: str,
    rule_id: str,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a terminology rule. Restricted to GOVERNANCE_ADMIN."""
    rule = await TerminologyRule.find_one(
        TerminologyRule.id == rule_id,
        TerminologyRule.workspace_id == workspace_id,
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RULE_NOT_FOUND", "message": "Terminology rule not found"}},
        )

    rule.active = False
    rule.updated_at = datetime.now(timezone.utc)
    await rule.save()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="TERMINOLOGY_RULE",
        entity_id=rule.id,
        action="TERMINOLOGY_RULE_DEACTIVATED",
        metadata_json={"term": rule.term},
    )

    return {"status": "success", "message": f"Rule for '{rule.term}' deactivated successfully"}


# ==========================================
# Visual Rules
# ==========================================

@router.get("/workspaces/{workspace_id}/visual-rules", response_model=List[VisualRuleResponse])
async def list_visual_rules(
    workspace_id: str,
    active_only: bool = Query(True),
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """List visual standards for the workspace."""
    query = [VisualRule.workspace_id == workspace_id]
    if active_only:
        query.append(VisualRule.active == True)

    rules = await VisualRule.find(*query).sort("-created_at").to_list()
    return [
        VisualRuleResponse(
            id=r.id,
            workspace_id=r.workspace_id,
            rule_type=r.rule_type,
            rule_config=r.rule_config,
            severity=r.severity,
            source_reference=r.source_reference,
            active=r.active,
            version=r.version,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.post("/workspaces/{workspace_id}/visual-rules", response_model=VisualRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_visual_rule(
    workspace_id: str,
    request: VisualRuleCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Create a new visual brand standard. Restricted to GOVERNANCE_ADMIN."""
    config = request.rule_config or {}
    if request.name:
        config["name"] = request.name
    if request.color_hex:
        config["color_hex"] = request.color_hex
    if request.tolerance_delta_e is not None:
        config["tolerance_delta_e"] = request.tolerance_delta_e
    if request.min_contrast_ratio is not None:
        config["min_contrast_ratio"] = request.min_contrast_ratio

    rule = VisualRule(
        workspace_id=workspace_id,
        rule_type=request.rule_type,
        rule_config=config,
        severity=request.severity,
        source_reference=request.source_reference,
        active=True,
        version=1,
    )
    await rule.insert()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="VISUAL_RULE",
        entity_id=rule.id,
        action="VISUAL_RULE_CREATED",
        metadata_json={"rule_type": rule.rule_type, "config": rule.rule_config},
    )

    return VisualRuleResponse(
        id=rule.id,
        workspace_id=rule.workspace_id,
        rule_type=rule.rule_type,
        rule_config=rule.rule_config,
        severity=rule.severity,
        source_reference=rule.source_reference,
        active=rule.active,
        version=rule.version,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/workspaces/{workspace_id}/visual-rules/{rule_id}", status_code=status.HTTP_200_OK)
async def delete_visual_rule(
    workspace_id: str,
    rule_id: str,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Deactivate a visual rule. Restricted to GOVERNANCE_ADMIN."""
    rule = await VisualRule.find_one(
        VisualRule.id == rule_id,
        VisualRule.workspace_id == workspace_id,
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RULE_NOT_FOUND", "message": "Visual rule not found"}},
        )

    rule.active = False
    rule.updated_at = datetime.now(timezone.utc)
    await rule.save()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="VISUAL_RULE",
        entity_id=rule.id,
        action="VISUAL_RULE_DEACTIVATED",
        metadata_json={"rule_type": rule.rule_type},
    )

    return {"status": "success", "message": "Visual rule deactivated successfully"}


# ==========================================
# Brand Assets
# ==========================================

@router.get("/workspaces/{workspace_id}/assets", response_model=List[BrandAssetResponse])
async def list_brand_assets(
    workspace_id: str,
    active_only: bool = Query(True),
    membership: Membership = Depends(require_workspace_role("CREATOR", "REVIEWER", "GOVERNANCE_ADMIN")),
):
    """List approved brand assets for the workspace."""
    query = [BrandAsset.workspace_id == workspace_id]
    if active_only:
        query.append(BrandAsset.active == True)

    assets = await BrandAsset.find(*query).sort("-created_at").to_list()
    return [
        BrandAssetResponse(
            id=a.id,
            workspace_id=a.workspace_id,
            name=a.name,
            asset_type=a.asset_type,
            storage_key=a.storage_key,
            file_hash=a.file_hash,
            metadata_json=a.metadata_json,
            active=a.active,
            created_at=a.created_at,
        )
        for a in assets
    ]


@router.post("/workspaces/{workspace_id}/assets", response_model=BrandAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_brand_asset(
    workspace_id: str,
    request: BrandAssetCreateRequest,
    membership: Membership = Depends(require_workspace_role("GOVERNANCE_ADMIN")),
    current_user: User = Depends(get_current_user),
):
    """Register an approved brand asset. Restricted to GOVERNANCE_ADMIN."""
    asset = BrandAsset(
        workspace_id=workspace_id,
        name=request.name,
        asset_type=request.asset_type,
        storage_key=request.storage_key,
        file_hash=request.file_hash or hashlib.sha256(request.name.encode()).hexdigest(),
        metadata_json=request.metadata_json,
        active=True,
    )
    await asset.insert()

    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="BRAND_ASSET",
        entity_id=asset.id,
        action="BRAND_ASSET_REGISTERED",
        metadata_json={"name": asset.name, "asset_type": asset.asset_type},
    )

    return BrandAssetResponse(
        id=asset.id,
        workspace_id=asset.workspace_id,
        name=asset.name,
        asset_type=asset.asset_type,
        storage_key=asset.storage_key,
        file_hash=asset.file_hash,
        metadata_json=asset.metadata_json,
        active=asset.active,
        created_at=asset.created_at,
    )
