"""API routes for Reviewer queue, comments, approvals, compliance certificates, and governance analytics."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response

from app.core.dependencies import get_current_user
from app.models.documents import (
    Approval,
    AuditEvent,
    AuditRun,
    ComplianceCertificate,
    ExceptionRequest,
    Finding,
    Membership,
    ReviewComment,
    Submission,
    SubmissionRevision,
    User,
    Workspace,
)
from app.schemas.reviews import (
    ApprovalRequest,
    ApprovalResponse,
    CertificateVerificationResponse,
    ComplianceCertificateResponse,
    ExceptionDecisionRequest,
    GovernanceInsightsResponse,
    RejectionRequest,
    ReviewCommentCreateRequest,
    ReviewCommentResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
)
from app.services.deterministic_engine import compute_readiness_score
from app.services.audit_verifier import record_audit_event

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def check_workspace_membership(
    workspace_id: str,
    user: User,
    allowed_roles: Optional[List[str]] = None,
) -> Membership:
    """Validates user is an active member with appropriate role."""
    if user.is_superuser:
        return Membership(workspace_id=workspace_id, user_id=user.id, role="GOVERNANCE_ADMIN")

    membership = await Membership.find_one(
        Membership.workspace_id == workspace_id,
        Membership.user_id == user.id,
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace.",
        )
    if allowed_roles and membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied. Required role in: {allowed_roles}, your role: {membership.role}",
        )
    return membership


# -------------------------------------------------------------------------
# 1. Reviewer Queue Endpoint
# -------------------------------------------------------------------------
@router.get(
    "/workspaces/{workspace_id}/reviews/queue",
    response_model=ReviewQueueResponse,
    summary="Get submissions awaiting reviewer action",
)
async def get_reviewer_queue(
    workspace_id: str,
    status_filter: str = Query("ALL", description="Filter by status: ALL, PENDING_REVIEW, NEEDS_CHANGES"),
    current_user: User = Depends(get_current_user),
):
    await check_workspace_membership(workspace_id, current_user)

    query = {"workspace_id": workspace_id}
    if status_filter != "ALL":
        query["status"] = status_filter

    submissions = await Submission.find(query).sort("-updated_at").to_list()
    queue_items = []

    for sub in submissions:
        latest_rev = await SubmissionRevision.find(
            SubmissionRevision.submission_id == sub.id
        ).sort("-revision_number").first_or_none()

        rev_count = await SubmissionRevision.find(
            SubmissionRevision.submission_id == sub.id
        ).count()

        latest_audit = None
        if latest_rev:
            latest_audit = await AuditRun.find(
                AuditRun.submission_id == sub.id,
                AuditRun.revision_id == latest_rev.id,
            ).sort("-created_at").first_or_none()

        # Count pending exceptions
        pending_exc = await ExceptionRequest.find(
            ExceptionRequest.submission_id == sub.id,
            ExceptionRequest.status == "PENDING",
        ).count()

        # Count comments
        comments_cnt = await ReviewComment.find(
            ReviewComment.submission_id == sub.id,
        ).count()

        # Creator email
        creator = await User.get(sub.created_by)

        crit_count = 0
        high_count = 0
        med_count = 0
        low_count = 0
        readiness_score = None

        if latest_audit:
            readiness_score = latest_audit.readiness_score
            findings = await Finding.find(Finding.audit_run_id == latest_audit.id).to_list()
            if findings:
                crit_count = sum(1 for f in findings if f.severity == "CRITICAL" and f.status not in ["RESOLVED", "EXCEPTION_APPROVED"])
                high_count = sum(1 for f in findings if f.severity == "HIGH" and f.status not in ["RESOLVED", "EXCEPTION_APPROVED"])
                med_count = sum(1 for f in findings if f.severity == "MEDIUM" and f.status not in ["RESOLVED", "EXCEPTION_APPROVED"])
                low_count = sum(1 for f in findings if f.severity == "LOW" and f.status not in ["RESOLVED", "EXCEPTION_APPROVED"])
            elif hasattr(latest_audit, "summary_counts") and latest_audit.summary_counts:
                counts = latest_audit.summary_counts or {}
                crit_count = counts.get("CRITICAL", 0)
                high_count = counts.get("HIGH", 0)
                med_count = counts.get("MEDIUM", 0)
                low_count = counts.get("LOW", 0)

        queue_items.append(
            ReviewQueueItem(
                submission_id=sub.id,
                title=sub.title,
                creator_id=sub.created_by,
                creator_email=creator.email if creator else None,
                format=getattr(sub, "input_type", "TEXT"),
                current_status=sub.status,
                revision_count=rev_count,
                latest_revision_id=latest_rev.id if latest_rev else "",
                readiness_score=readiness_score,
                critical_findings=crit_count,
                high_findings=high_count,
                medium_findings=med_count,
                low_findings=low_count,
                pending_exceptions=pending_exc,
                comments_count=comments_cnt,
                updated_at=sub.updated_at,
            )
        )

    return ReviewQueueResponse(
        workspace_id=workspace_id,
        total_count=len(queue_items),
        items=queue_items,
    )


# -------------------------------------------------------------------------
# 2. Reviewer Comments Endpoints
# -------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/comments",
    response_model=ReviewCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an inline review comment to a submission",
)
async def add_review_comment(
    submission_id: str,
    payload: ReviewCommentCreateRequest,
    current_user: User = Depends(get_current_user),
):
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    await check_workspace_membership(submission.workspace_id, current_user)

    revision_id = payload.revision_id
    if not revision_id:
        latest_rev = await SubmissionRevision.find(
            SubmissionRevision.submission_id == submission.id
        ).sort("-revision_number").first_or_none()
        if not latest_rev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No revision found for submission")
        revision_id = latest_rev.id

    comment = ReviewComment(
        submission_id=submission.id,
        revision_id=revision_id,
        user_id=current_user.id,
        comment_text=payload.comment_text,
        anchor_location=payload.anchor_location,
        created_at=utc_now(),
    )
    await comment.insert()

    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="ReviewComment",
        entity_id=comment.id,
        action="COMMENT_ADDED",
        metadata_json={
            "submission_id": submission.id,
            "revision_id": revision_id,
            "anchor_location": payload.anchor_location,
        },
    )

    return ReviewCommentResponse(
        id=comment.id,
        submission_id=comment.submission_id,
        revision_id=comment.revision_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        user_email=current_user.email,
        comment_text=comment.comment_text,
        anchor_location=comment.anchor_location,
        created_at=comment.created_at,
    )


@router.get(
    "/submissions/{submission_id}/comments",
    response_model=List[ReviewCommentResponse],
    summary="List all review comments for a submission",
)
async def list_review_comments(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    await check_workspace_membership(submission.workspace_id, current_user)

    comments = await ReviewComment.find(
        ReviewComment.submission_id == submission_id
    ).sort("created_at").to_list()

    responses = []
    user_cache = {}
    for c in comments:
        if c.user_id not in user_cache:
            u = await User.get(c.user_id)
            user_cache[c.user_id] = u
        u = user_cache[c.user_id]

        responses.append(
            ReviewCommentResponse(
                id=c.id,
                submission_id=c.submission_id,
                revision_id=c.revision_id,
                user_id=c.user_id,
                user_name=u.full_name if u else None,
                user_email=u.email if u else None,
                comment_text=c.comment_text,
                anchor_location=c.anchor_location,
                created_at=c.created_at,
            )
        )
    return responses


# -------------------------------------------------------------------------
# 3. Exception Decision Endpoint
# -------------------------------------------------------------------------
@router.post(
    "/exceptions/{exception_id}/decide",
    summary="Approve or reject a creator exception request (Reviewer/Admin only)",
)
async def decide_exception(
    exception_id: str,
    payload: ExceptionDecisionRequest,
    current_user: User = Depends(get_current_user),
):
    exception = await ExceptionRequest.get(exception_id)
    if not exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception request not found")

    submission = await Submission.get(exception.submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated submission not found")

    await check_workspace_membership(
        submission.workspace_id,
        current_user,
        allowed_roles=["REVIEWER", "GOVERNANCE_ADMIN"],
    )

    now = utc_now()
    exception.status = payload.decision
    exception.decided_by = current_user.id
    exception.decision_note = payload.decision_note
    exception.decided_at = now
    await exception.save()

    finding = await Finding.get(exception.finding_id)
    if finding:
        if payload.decision == "APPROVED":
            finding.status = "EXCEPTION_APPROVED"
        else:
            finding.status = "EXCEPTION_REJECTED"
        await finding.save()

        # Recalculate Brand Readiness Score for the latest audit run
        audit_run = await AuditRun.get(finding.audit_run_id)
        if audit_run:
            all_findings = await Finding.find(Finding.audit_run_id == audit_run.id).to_list()
            audit_run.readiness_score = compute_readiness_score(all_findings)
            await audit_run.save()

    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="ExceptionRequest",
        entity_id=exception.id,
        action="EXCEPTION_DECIDED",
        metadata_json={
            "decision": payload.decision,
            "decision_note": payload.decision_note,
            "finding_id": exception.finding_id,
            "submission_id": submission.id,
        },
    )

    return {
        "id": exception.id,
        "finding_id": exception.finding_id,
        "submission_id": exception.submission_id,
        "status": exception.status,
        "decided_by": exception.decided_by,
        "decision_note": exception.decision_note,
        "decided_at": exception.decided_at,
    }


# -------------------------------------------------------------------------
# 4. Sign-Off Approval & Rejection Endpoints
# -------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/approve",
    response_model=ApprovalResponse,
    summary="Reviewer formal approval & sign-off; issues tamper-evident compliance certificate",
)
async def approve_submission(
    submission_id: str,
    payload: ApprovalRequest,
    current_user: User = Depends(get_current_user),
):
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    workspace = await Workspace.get(submission.workspace_id)
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    # Acceptance Criterion: Creator cannot approve their own submission
    if submission.created_by == current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creators cannot approve their own submissions. A separate Reviewer or Governance Admin must sign off.",
        )

    # RBAC: Only REVIEWER or GOVERNANCE_ADMIN can approve
    await check_workspace_membership(
        submission.workspace_id,
        current_user,
        allowed_roles=["REVIEWER", "GOVERNANCE_ADMIN"],
    )

    # Get latest revision
    latest_rev = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("-revision_number").first_or_none()
    if not latest_rev:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No revision found to approve")

    # Get latest audit run
    latest_audit = await AuditRun.find(
        AuditRun.submission_id == submission.id,
        AuditRun.revision_id == latest_rev.id,
    ).sort("-created_at").first_or_none()

    # Verify score threshold and critical findings
    readiness_score = latest_audit.readiness_score if latest_audit else 100
    findings_summary = {}
    if latest_audit:
        all_audit_findings = await Finding.find(Finding.audit_run_id == latest_audit.id).to_list()
        open_critical_or_high = [
            f for f in all_audit_findings
            if f.severity in ["CRITICAL", "HIGH"] and f.status == "OPEN"
        ]
        findings_summary = {
            "CRITICAL": sum(1 for f in all_audit_findings if f.severity == "CRITICAL"),
            "HIGH": sum(1 for f in all_audit_findings if f.severity == "HIGH"),
            "MEDIUM": sum(1 for f in all_audit_findings if f.severity == "MEDIUM"),
            "LOW": sum(1 for f in all_audit_findings if f.severity == "LOW"),
        }

        if readiness_score < 85 and len(open_critical_or_high) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve submission: Brand Readiness Score ({readiness_score}%) is below 85% with {len(open_critical_or_high)} unresolved critical/high findings.",
            )

    now = utc_now()
    submission.status = "APPROVED"
    submission.updated_at = now
    await submission.save()

    approval = Approval(
        submission_id=submission.id,
        revision_id=latest_rev.id,
        decided_by=current_user.id,
        decision="APPROVED",
        decision_notes=payload.decision_notes,
        readiness_score_at_approval=readiness_score,
        created_at=now,
    )
    await approval.insert()

    # Generate Compliance Certificate
    cert_slug = workspace.slug.upper()[:8].replace("-", "")
    cert_number = f"VBT-CERT-{cert_slug}-{uuid.uuid4().hex[:8].upper()}"
    issued_at_iso = now.isoformat()
    cert_payload = {
        "certificate_number": cert_number,
        "submission_id": submission.id,
        "revision_id": latest_rev.id,
        "revision_hash": latest_rev.content_hash,
        "workspace_id": workspace.id,
        "approval_id": approval.id,
        "decided_by": current_user.id,
        "readiness_score": readiness_score,
        "issued_at": issued_at_iso,
    }
    cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()

    certificate = ComplianceCertificate(
        approval_id=approval.id,
        submission_id=submission.id,
        workspace_id=workspace.id,
        certificate_number=cert_number,
        certificate_hash=cert_hash,
        issued_at=now,
        metadata_json={
            "submission_title": submission.title,
            "workspace_name": workspace.name,
            "workspace_slug": workspace.slug,
            "readiness_score": readiness_score,
            "approver_email": current_user.email,
            "approver_name": current_user.full_name,
            "revision_number": latest_rev.revision_number,
            "revision_content_hash": latest_rev.content_hash,
            "issued_at_iso": issued_at_iso,
            "findings_summary": findings_summary,
        },
    )
    await certificate.insert()

    # Record SHA-256 chained audit events
    await record_audit_event(
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        entity_type="Submission",
        entity_id=submission.id,
        action="SUBMISSION_APPROVED",
        metadata_json={
            "approval_id": approval.id,
            "revision_id": latest_rev.id,
            "readiness_score": readiness_score,
            "decision_notes": payload.decision_notes,
        },
    )

    await record_audit_event(
        workspace_id=workspace.id,
        actor_user_id=current_user.id,
        entity_type="ComplianceCertificate",
        entity_id=certificate.id,
        action="COMPLIANCE_CERTIFICATE_ISSUED",
        metadata_json={
            "certificate_number": cert_number,
            "certificate_hash": cert_hash,
            "submission_id": submission.id,
        },
    )

    cert_response = ComplianceCertificateResponse(
        id=certificate.id,
        certificate_number=certificate.certificate_number,
        submission_id=certificate.submission_id,
        approval_id=certificate.approval_id,
        workspace_id=certificate.workspace_id,
        certificate_hash=certificate.certificate_hash,
        issued_at=certificate.issued_at,
        metadata_json=certificate.metadata_json,
    )

    return ApprovalResponse(
        id=approval.id,
        submission_id=approval.submission_id,
        revision_id=approval.revision_id,
        decided_by=approval.decided_by,
        decided_by_email=current_user.email,
        decision=approval.decision,
        decision_notes=approval.decision_notes,
        readiness_score_at_approval=approval.readiness_score_at_approval,
        created_at=approval.created_at,
        certificate=cert_response,
    )


@router.post(
    "/submissions/{submission_id}/reject",
    response_model=ApprovalResponse,
    summary="Reviewer formal rejection / request changes with required justification",
)
async def reject_submission(
    submission_id: str,
    payload: RejectionRequest,
    current_user: User = Depends(get_current_user),
):
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    await check_workspace_membership(
        submission.workspace_id,
        current_user,
        allowed_roles=["REVIEWER", "GOVERNANCE_ADMIN"],
    )

    latest_rev = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("-revision_number").first_or_none()
    if not latest_rev:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No revision found to reject")

    latest_audit = await AuditRun.find(
        AuditRun.submission_id == submission.id,
        AuditRun.revision_id == latest_rev.id,
    ).sort("-created_at").first_or_none()

    now = utc_now()
    submission.status = "NEEDS_CHANGES"
    submission.updated_at = now
    await submission.save()

    approval = Approval(
        submission_id=submission.id,
        revision_id=latest_rev.id,
        decided_by=current_user.id,
        decision="REJECTED",
        decision_notes=payload.decision_notes,
        readiness_score_at_approval=latest_audit.readiness_score if latest_audit else 0,
        created_at=now,
    )
    await approval.insert()

    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="Submission",
        entity_id=submission.id,
        action="SUBMISSION_REJECTED",
        metadata_json={
            "approval_id": approval.id,
            "revision_id": latest_rev.id,
            "decision_notes": payload.decision_notes,
        },
    )

    return ApprovalResponse(
        id=approval.id,
        submission_id=approval.submission_id,
        revision_id=approval.revision_id,
        decided_by=approval.decided_by,
        decided_by_email=current_user.email,
        decision=approval.decision,
        decision_notes=approval.decision_notes,
        readiness_score_at_approval=approval.readiness_score_at_approval,
        created_at=approval.created_at,
        certificate=None,
    )


# -------------------------------------------------------------------------
# 5. Compliance Certificate Endpoints
# -------------------------------------------------------------------------
@router.get(
    "/submissions/{submission_id}/certificate",
    response_model=ComplianceCertificateResponse,
    summary="Get compliance certificate for an approved submission",
)
async def get_submission_certificate(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    await check_workspace_membership(submission.workspace_id, current_user)

    cert = await ComplianceCertificate.find_one(
        ComplianceCertificate.submission_id == submission_id
    )
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No certificate issued for this submission")

    return ComplianceCertificateResponse(
        id=cert.id,
        certificate_number=cert.certificate_number,
        submission_id=cert.submission_id,
        approval_id=cert.approval_id,
        workspace_id=cert.workspace_id,
        certificate_hash=cert.certificate_hash,
        issued_at=cert.issued_at,
        metadata_json=cert.metadata_json,
    )


@router.get(
    "/certificates/{certificate_number}/verify",
    response_model=CertificateVerificationResponse,
    summary="Public verification endpoint to mathematically verify certificate cryptographic authenticity",
)
async def verify_certificate_authenticity(certificate_number: str):
    cert = await ComplianceCertificate.find_one(
        ComplianceCertificate.certificate_number == certificate_number
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_number}' does not exist or has been revoked.",
        )

    approval = await Approval.get(cert.approval_id)
    submission = await Submission.get(cert.submission_id)
    workspace = await Workspace.get(cert.workspace_id)
    approver = await User.get(approval.decided_by) if approval else None

    # Reconstruct exact cryptographic payload to verify SHA-256 integrity
    meta = cert.metadata_json or {}
    issued_iso = meta.get("issued_at_iso") or cert.issued_at.isoformat()
    cert_payload = {
        "certificate_number": cert.certificate_number,
        "submission_id": cert.submission_id,
        "revision_id": approval.revision_id if approval else "",
        "revision_hash": meta.get("revision_content_hash", ""),
        "workspace_id": cert.workspace_id,
        "approval_id": cert.approval_id,
        "decided_by": approval.decided_by if approval else "",
        "readiness_score": approval.readiness_score_at_approval if approval else 0,
        "issued_at": issued_iso,
    }
    computed_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode("utf-8")).hexdigest()
    is_valid = (computed_hash == cert.certificate_hash)

    return CertificateVerificationResponse(
        valid=is_valid,
        certificate_number=cert.certificate_number,
        certificate_hash=cert.certificate_hash,
        computed_hash=computed_hash,
        submission_title=submission.title if submission else "Unknown Submission",
        submission_id=cert.submission_id,
        workspace_name=workspace.name if workspace else "Unknown Workspace",
        readiness_score=approval.readiness_score_at_approval if approval else 0,
        decided_by_email=approver.email if approver else "Unknown Approver",
        issued_at=cert.issued_at,
        tamper_evident_verified=is_valid,
    )


@router.get(
    "/certificates/{certificate_number}/download",
    summary="Download officially sealed PDF compliance certificate with embedded QR code",
)
async def download_certificate_pdf(certificate_number: str):
    cert = await ComplianceCertificate.find_one(
        ComplianceCertificate.certificate_number == certificate_number
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_number}' does not exist or has been revoked.",
        )

    approval = await Approval.get(cert.approval_id)
    submission = await Submission.get(cert.submission_id)
    workspace = await Workspace.get(cert.workspace_id)
    approver = await User.get(approval.decided_by) if approval else None

    # Generate vector PDF bytes with embedded QR code
    from app.services.certificate_generator import generate_compliance_certificate_pdf

    readiness_score = approval.readiness_score_at_approval if approval else 90
    approver_name = (approver.full_name or "Authorized Brand Reviewer") if approver else "Authorized Reviewer"
    approver_email = approver.email if approver else "reviewer@veribrand.io"

    pdf_bytes = generate_compliance_certificate_pdf(
        certificate_number=cert.certificate_number,
        certificate_hash=cert.certificate_hash,
        submission_title=submission.title if submission else "Corporate Asset Publication",
        workspace_name=workspace.name if workspace else "Enterprise Brand Workspace",
        readiness_score=readiness_score,
        approver_name=approver_name,
        approver_email=approver_email,
        issued_at=cert.issued_at,
        verification_url=f"https://veribrand-trace.vercel.app/verify/{cert.certificate_number}",
        metadata_json=cert.metadata_json,
    )

    filename = f"VeriBrand_Certificate_{cert.certificate_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


# -------------------------------------------------------------------------
# 6. Governance Insights & Analytics Endpoint
# -------------------------------------------------------------------------
@router.get(
    "/workspaces/{workspace_id}/governance/insights",
    response_model=GovernanceInsightsResponse,
    summary="Retrieve aggregate governance analytics and recurring compliance violation patterns",
)
async def get_governance_insights(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
):
    await check_workspace_membership(
        workspace_id,
        current_user,
        allowed_roles=["GOVERNANCE_ADMIN", "REVIEWER"],
    )

    submissions = await Submission.find(Submission.workspace_id == workspace_id).to_list()
    total_submissions = len(submissions)
    total_approved = sum(1 for s in submissions if s.status == "APPROVED")
    total_rejected = sum(1 for s in submissions if s.status in ["REJECTED", "NEEDS_CHANGES"])
    total_pending = sum(1 for s in submissions if s.status in ["PENDING_REVIEW", "PROCESSING", "DRAFT"])

    approval_rate = round((total_approved / total_submissions * 100), 1) if total_submissions > 0 else 0.0

    # Aggregate readiness scores and findings from audit runs
    sub_ids = [s.id for s in submissions]
    audit_runs = await AuditRun.find({"submission_id": {"$in": sub_ids}}).to_list()

    avg_score = 0.0
    if audit_runs:
        avg_score = round(sum(a.readiness_score for a in audit_runs) / len(audit_runs), 1)

    # Exceptions aggregate
    exceptions = await ExceptionRequest.find({"submission_id": {"$in": sub_ids}}).to_list()
    total_exc = len(exceptions)
    total_exc_app = sum(1 for e in exceptions if e.status == "APPROVED")
    total_exc_rej = sum(1 for e in exceptions if e.status == "REJECTED")

    # Findings categories and top violated rules
    run_ids = [a.id for a in audit_runs]
    findings = await Finding.find({"audit_run_id": {"$in": run_ids}}).to_list()

    cat_counts: dict[str, int] = {}
    sev_counts: dict[str, int] = {}
    rule_counts: dict[str, int] = {}

    for f in findings:
        cat_counts[f.category] = cat_counts.get(f.category, 0) + 1
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
        # Extract rule identifier from title or evidence
        rule_key = f.title
        rule_counts[rule_key] = rule_counts.get(rule_key, 0) + 1

    top_rules = [
        {"rule_title": title, "count": count}
        for title, count in sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return GovernanceInsightsResponse(
        workspace_id=workspace_id,
        total_submissions=total_submissions,
        total_approved=total_approved,
        total_rejected=total_rejected,
        total_pending=total_pending,
        approval_rate=approval_rate,
        avg_readiness_score=avg_score,
        total_exceptions_requested=total_exc,
        total_exceptions_approved=total_exc_app,
        total_exceptions_rejected=total_exc_rej,
        category_breakdown=cat_counts,
        top_violated_rules=top_rules,
        severity_breakdown=sev_counts,
    )
