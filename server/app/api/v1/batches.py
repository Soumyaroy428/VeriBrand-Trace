"""Batch Processing API Endpoints.

Enables multi-asset marketing campaign verification:
- Bulk content submission with privacy scrubbing.
- Concurrent deterministic rule scanning and grounded RAG verification.
- Campaign readiness metrics and executive governance export.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.core.dependencies import get_current_user
from app.models.documents import User, Workspace, Membership, BatchAudit
from app.schemas.batches import (
    BatchCreateRequest,
    BatchAuditResponse,
    BatchExportReport,
)
from app.services.batch_processor import batch_processor

router = APIRouter()


async def verify_workspace_access(
    workspace_id: str,
    user: User,
    required_role: Optional[str] = None,
) -> Membership:
    """Verifies that the user belongs to the workspace with sufficient privileges."""
    membership = await Membership.find_one(
        Membership.workspace_id == workspace_id,
        Membership.user_id == user.id,
    )
    if not membership and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you are not a member of this workspace",
        )

    if required_role and membership and not user.is_superuser:
        role_hierarchy = {"CREATOR": 1, "REVIEWER": 2, "GOVERNANCE_ADMIN": 3}
        user_rank = role_hierarchy.get(membership.role, 0)
        req_rank = role_hierarchy.get(required_role, 0)
        if user_rank < req_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role} privileges",
            )

    return membership


@router.post(
    "/workspaces/{workspace_id}/batches",
    response_model=BatchAuditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and optionally execute a multi-item campaign batch audit",
)
async def create_batch_audit(
    workspace_id: str,
    payload: BatchCreateRequest,
    auto_run: bool = Query(True, description="Immediately execute audit on all items"),
    current_user: User = Depends(get_current_user),
):
    """Creates a campaign batch audit from multiple content items and optionally triggers verification."""
    await verify_workspace_access(workspace_id, current_user)

    batch = await batch_processor.create_batch(
        workspace_id=workspace_id,
        user_id=current_user.id,
        title=payload.title,
        campaign_tag=payload.campaign_tag,
        items=payload.items,
    )

    if auto_run:
        batch = await batch_processor.execute_batch(
            batch=batch,
            actor_user_id=current_user.id,
        )

    item_summaries = await batch_processor.get_batch_items_summary(batch)

    return BatchAuditResponse(
        id=batch.id,
        workspace_id=batch.workspace_id,
        title=batch.title,
        campaign_tag=batch.campaign_tag,
        created_by=batch.created_by,
        status=batch.status,
        total_items=batch.total_items,
        completed_items=batch.completed_items,
        aggregate_score=batch.aggregate_score,
        critical_violations=batch.critical_violations,
        warning_violations=batch.warning_violations,
        info_violations=batch.info_violations,
        campaign_rating=batch.campaign_rating,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        items=item_summaries,
    )


@router.get(
    "/workspaces/{workspace_id}/batches",
    response_model=List[BatchAuditResponse],
    summary="List all campaign batch audits in workspace",
)
async def list_workspace_batches(
    workspace_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    campaign_tag: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Returns paginated campaign batch audits for the active brand workspace."""
    await verify_workspace_access(workspace_id, current_user)

    criteria = [BatchAudit.workspace_id == workspace_id]
    if campaign_tag:
        criteria.append(BatchAudit.campaign_tag == campaign_tag)

    batches = await BatchAudit.find(*criteria).sort("-created_at").skip(skip).limit(limit).to_list()

    responses = []
    for b in batches:
        summaries = await batch_processor.get_batch_items_summary(b)
        responses.append(
            BatchAuditResponse(
                id=b.id,
                workspace_id=b.workspace_id,
                title=b.title,
                campaign_tag=b.campaign_tag,
                created_by=b.created_by,
                status=b.status,
                total_items=b.total_items,
                completed_items=b.completed_items,
                aggregate_score=b.aggregate_score,
                critical_violations=b.critical_violations,
                warning_violations=b.warning_violations,
                info_violations=b.info_violations,
                campaign_rating=b.campaign_rating,
                created_at=b.created_at,
                updated_at=b.updated_at,
                items=summaries,
            )
        )

    return responses


@router.get(
    "/workspaces/{workspace_id}/batches/{batch_id}",
    response_model=BatchAuditResponse,
    summary="Get single campaign batch status and item breakdown",
)
async def get_batch_details(
    workspace_id: str,
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves full status and itemized finding breakdown of a campaign batch."""
    await verify_workspace_access(workspace_id, current_user)

    batch = await BatchAudit.get(batch_id)
    if not batch or batch.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch audit not found in this workspace",
        )

    item_summaries = await batch_processor.get_batch_items_summary(batch)

    return BatchAuditResponse(
        id=batch.id,
        workspace_id=batch.workspace_id,
        title=batch.title,
        campaign_tag=batch.campaign_tag,
        created_by=batch.created_by,
        status=batch.status,
        total_items=batch.total_items,
        completed_items=batch.completed_items,
        aggregate_score=batch.aggregate_score,
        critical_violations=batch.critical_violations,
        warning_violations=batch.warning_violations,
        info_violations=batch.info_violations,
        campaign_rating=batch.campaign_rating,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        items=item_summaries,
    )


@router.post(
    "/workspaces/{workspace_id}/batches/{batch_id}/run",
    response_model=BatchAuditResponse,
    summary="Execute or re-run a campaign batch audit",
)
async def run_batch_audit(
    workspace_id: str,
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """Triggers end-to-end audit on all items of an existing campaign batch."""
    await verify_workspace_access(workspace_id, current_user)

    batch = await BatchAudit.get(batch_id)
    if not batch or batch.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch audit not found in this workspace",
        )

    batch = await batch_processor.execute_batch(
        batch=batch,
        actor_user_id=current_user.id,
    )

    item_summaries = await batch_processor.get_batch_items_summary(batch)

    return BatchAuditResponse(
        id=batch.id,
        workspace_id=batch.workspace_id,
        title=batch.title,
        campaign_tag=batch.campaign_tag,
        created_by=batch.created_by,
        status=batch.status,
        total_items=batch.total_items,
        completed_items=batch.completed_items,
        aggregate_score=batch.aggregate_score,
        critical_violations=batch.critical_violations,
        warning_violations=batch.warning_violations,
        info_violations=batch.info_violations,
        campaign_rating=batch.campaign_rating,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        items=item_summaries,
    )


@router.get(
    "/workspaces/{workspace_id}/batches/{batch_id}/export",
    response_model=BatchExportReport,
    summary="Export executive campaign governance report",
)
async def export_batch_report(
    workspace_id: str,
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """Exports structured executive summary and per-item governance statistics."""
    await verify_workspace_access(workspace_id, current_user)

    batch = await BatchAudit.get(batch_id)
    if not batch or batch.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch audit not found in this workspace",
        )

    return await batch_processor.export_batch_report(batch)
