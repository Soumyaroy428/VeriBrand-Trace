"""Audit Execution & Findings API Endpoints.

Handles:
- Starting deterministic brand governance audits on submission revisions.
- Audit run progress, status, and Brand Readiness Score inspection.
- Traceable finding cards with source evidence citations and suggestions.
- Cryptographic SHA-256 chained audit trail recording.
"""

import re
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Query

from app.core.dependencies import get_current_user
from app.models.documents import (
    User,
    Membership,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    FindingEvidence,
    AuditEvent,
    ExceptionRequest,
)
from app.schemas.audits import (
    AuditRunResponse,
    FindingResponse,
    FindingEvidenceResponse,
    AuditRunWithFindingsResponse,
    ExceptionCreateRequest,
    ExceptionResponse,
    ApplySuggestionRequest,
    DiffResponse,
)
from app.schemas.submissions import SubmissionRevisionResponse
from app.services.deterministic_engine import deterministic_engine, compute_readiness_score
from app.services.rag_engine import rag_engine
from app.services.ai_claim_verifier import ai_claim_verifier
from app.services.diff_engine import diff_engine
from app.services.storage import storage_service
from app.services.privacy import privacy_service
from app.services.audit_verifier import record_audit_event

router = APIRouter()


async def build_audit_run_response(audit_run: AuditRun) -> AuditRunResponse:
    """Computes finding counts and shapes AuditRunResponse."""
    findings = await Finding.find(Finding.audit_run_id == audit_run.id).to_list()
    crit = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    med = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")

    return AuditRunResponse(
        id=audit_run.id,
        submission_id=audit_run.submission_id,
        revision_id=audit_run.revision_id,
        status=audit_run.status,
        deterministic_status=audit_run.deterministic_status,
        ai_status=audit_run.ai_status,
        readiness_score=audit_run.readiness_score,
        model_identifier=audit_run.model_identifier,
        rule_set_version=audit_run.rule_set_version,
        started_at=audit_run.started_at,
        completed_at=audit_run.completed_at,
        error_code=audit_run.error_code,
        created_at=audit_run.created_at,
        total_findings=len(findings),
        critical_findings=crit,
        high_findings=high,
        medium_findings=med,
        low_findings=low,
    )


async def build_finding_response(finding: Finding) -> FindingResponse:
    """Attaches evidence citations to finding response."""
    evidences = await FindingEvidence.find(FindingEvidence.finding_id == finding.id).to_list()
    evidence_items = [
        FindingEvidenceResponse(
            id=e.id,
            finding_id=e.finding_id,
            source_type=e.source_type,
            source_id=e.source_id,
            source_version=e.source_version,
            quote=e.quote,
            location=e.location,
            created_at=e.created_at,
        )
        for e in evidences
    ]

    return FindingResponse(
        id=finding.id,
        audit_run_id=finding.audit_run_id,
        category=finding.category,
        severity=finding.severity,
        source_engine=finding.source_engine,
        title=finding.title,
        description=finding.description,
        location=finding.location,
        evidence=finding.evidence,
        suggestion=finding.suggestion,
        status=finding.status,
        created_at=finding.created_at,
        evidence_list=evidence_items,
    )


# --- 1. Start Audit on Latest Revision ---

@router.post(
    "/submissions/{submission_id}/audits",
    response_model=AuditRunWithFindingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger deterministic verification on latest submission revision",
)
async def start_submission_audit(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    """Executes deterministic audit pipeline on submission."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    # Validate workspace membership
    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you are not a member of this workspace",
        )

    # Get latest revision
    latest_rev = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("-revision_number").first_or_none()

    if not latest_rev:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission has no revisions to audit",
        )

    # 1. Execute Deterministic Engine
    audit_run, findings = await deterministic_engine.run_audit(
        submission=submission,
        revision=latest_rev,
    )

    # 2. Workspace-Scoped Evidence Retrieval (RAG)
    text_to_audit = latest_rev.sanitized_text or latest_rev.extracted_text or latest_rev.raw_content or ""
    evidence_passages = await rag_engine.retrieve_evidence(
        workspace_id=submission.workspace_id,
        query=text_to_audit,
        top_k=5,
    )

    # 3. Grounded AI Claim & Tone Verification (Gemini 2.5 Flash)
    ai_findings_raw, ai_status, ai_err = await ai_claim_verifier.verify_claims(
        sanitized_text=text_to_audit,
        retrieved_evidence=evidence_passages,
        workspace_id=submission.workspace_id,
    )

    # Normalize and persist AI findings
    for ai_f in ai_findings_raw:
        finding_doc = Finding(
            audit_run_id=audit_run.id,
            category=ai_f.category,
            severity=ai_f.severity,
            source_engine="RAG_AI",
            title=ai_f.title,
            description=ai_f.explanation,
            location={"claim_text": ai_f.claim_text},
            evidence={
                "source_citation": ai_f.source_citation,
                "quote": ai_f.retrieved_evidence_quote,
                "is_grounded": ai_f.is_grounded,
                "confidence_score": ai_f.confidence_score,
                "verdict": ai_f.verdict,
            },
            suggestion={
                "action": "REWRITE_CLAIM",
                "original": ai_f.claim_text,
                "suggested_text": ai_f.suggested_correction,
            } if ai_f.suggested_correction else None,
            status="OPEN",
        )
        await finding_doc.insert()

        # Attach Evidence Passage
        if ai_f.retrieved_evidence_quote or ai_f.source_citation:
            ev_doc = FindingEvidence(
                finding_id=finding_doc.id,
                source_type="GUIDELINE_CHUNK" if "guideline" in (ai_f.source_citation or "").lower() else "APPROVED_FACT",
                source_version=1,
                quote=ai_f.retrieved_evidence_quote or "No verified evidence found in Brand Vault.",
                location={"citation": ai_f.source_citation},
            )
            await ev_doc.insert()

        findings.append(finding_doc)

    # 4. Finalize AuditRun and Recompute Readiness Score
    final_score = compute_readiness_score(findings)
    audit_run.readiness_score = final_score
    audit_run.ai_status = ai_status
    audit_run.model_identifier = "gemini-2.5-flash"
    if ai_err:
        audit_run.error_code = ai_err
    await audit_run.save()

    # Update Submission status
    has_blocking = any(f.severity in ["CRITICAL", "HIGH"] for f in findings)
    if has_blocking:
        submission.status = "NEEDS_CHANGES"
    elif final_score >= 85:
        submission.status = "PENDING_REVIEW"
    await submission.save()

    # 5. Record SHA-256 Chained Audit Event
    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="AUDIT_RUN",
        entity_id=audit_run.id,
        action="FULL_AUDIT_COMPLETED",
        metadata_json={
            "submission_id": submission.id,
            "revision_number": latest_rev.revision_number,
            "readiness_score": final_score,
            "total_findings": len(findings),
            "deterministic_findings_count": len([f for f in findings if f.source_engine == "DETERMINISTIC"]),
            "ai_findings_count": len([f for f in findings if f.source_engine == "RAG_AI"]),
            "critical_count": sum(1 for f in findings if f.severity == "CRITICAL"),
            "high_count": sum(1 for f in findings if f.severity == "HIGH"),
        },
    )

    audit_run_res = await build_audit_run_response(audit_run)
    finding_res_list = [await build_finding_response(f) for f in findings]

    return AuditRunWithFindingsResponse(
        audit_run=audit_run_res,
        findings=finding_res_list,
    )


# --- 2. Get Audit Status & Summary ---

@router.get(
    "/audits/{audit_id}",
    response_model=AuditRunResponse,
    summary="Get audit run status and readiness metrics",
)
async def get_audit_status(
    audit_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves audit run details."""
    audit_run = await AuditRun.get(audit_id)
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit run not found",
        )

    submission = await Submission.get(audit_run.submission_id)
    if submission:
        membership = await Membership.find_one(
            Membership.workspace_id == submission.workspace_id,
            Membership.user_id == current_user.id,
        )
        if not membership and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden",
            )

    return await build_audit_run_response(audit_run)


# --- 3. Get Audit Findings with Evidence Citations ---

@router.get(
    "/audits/{audit_id}/findings",
    response_model=List[FindingResponse],
    summary="List all findings with evidence and suggestions",
)
async def get_audit_findings(
    audit_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves all findings for an audit run."""
    audit_run = await AuditRun.get(audit_id)
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit run not found",
        )

    submission = await Submission.get(audit_run.submission_id)
    if submission:
        membership = await Membership.find_one(
            Membership.workspace_id == submission.workspace_id,
            Membership.user_id == current_user.id,
        )
        if not membership and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden",
            )

    findings = await Finding.find(Finding.audit_run_id == audit_run.id).to_list()
    return [await build_finding_response(f) for f in findings]


# --- 4. Get Latest Audit for Submission ---

@router.get(
    "/submissions/{submission_id}/latest-audit",
    response_model=AuditRunWithFindingsResponse,
    summary="Get the most recent audit run and findings for a submission",
)
async def get_latest_submission_audit(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves the latest audit run with all finding details."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    latest_audit = await AuditRun.find(
        AuditRun.submission_id == submission.id
    ).sort("-created_at").first_or_none()

    if not latest_audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No audit runs found for this submission",
        )

    findings = await Finding.find(Finding.audit_run_id == latest_audit.id).to_list()
    audit_run_res = await build_audit_run_response(latest_audit)
    finding_res_list = [await build_finding_response(f) for f in findings]

    return AuditRunWithFindingsResponse(
        audit_run=audit_run_res,
        findings=finding_res_list,
    )


# --- 5. Helper to Build SubmissionRevisionResponse ---

def to_revision_response(rev: SubmissionRevision) -> SubmissionRevisionResponse:
    """Converts SubmissionRevision document to response schema."""
    return SubmissionRevisionResponse(
        id=rev.id,
        submission_id=rev.submission_id,
        revision_number=rev.revision_number,
        storage_key=rev.storage_key,
        content_hash=rev.content_hash,
        extracted_text=rev.extracted_text,
        sanitized_text=rev.sanitized_text,
        privacy_gate_metadata=rev.privacy_gate_metadata,
        created_by=rev.created_by,
        created_at=rev.created_at,
    )


# --- 6. Explainable Diff Endpoint ---

@router.get(
    "/submissions/{submission_id}/diff",
    response_model=DiffResponse,
    summary="Calculate synchronized word-level and line-level diff between revisions",
)
async def get_submission_diff(
    submission_id: str,
    from_rev: Optional[int] = Query(None, description="Source revision number (defaults to v1)"),
    to_rev: Optional[int] = Query(None, description="Target revision number (defaults to latest)"),
    current_user: User = Depends(get_current_user),
):
    """Calculates structured side-by-side diff between two revisions of a submission."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you are not a member of this workspace",
        )

    revisions = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("revision_number").to_list()

    if not revisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission has no revisions to compare",
        )

    # Determine from and to revisions
    rev_map = {r.revision_number: r for r in revisions}
    from_num = from_rev if (from_rev and from_rev in rev_map) else revisions[0].revision_number
    to_num = to_rev if (to_rev and to_rev in rev_map) else revisions[-1].revision_number

    from_revision = rev_map[from_num]
    to_revision = rev_map[to_num]

    orig_text = from_revision.extracted_text or from_revision.raw_content or ""
    rev_text = to_revision.extracted_text or to_revision.raw_content or ""

    return diff_engine.generate_diff(
        submission_id=submission.id,
        from_rev_num=from_num,
        to_rev_num=to_num,
        original_text=orig_text,
        revised_text=rev_text,
    )


# --- 7. Accept / Apply Suggestion Endpoint ---

@router.post(
    "/submissions/{submission_id}/apply-suggestion",
    summary="Accept an intent-preserving suggestion and create an incremental revision",
)
async def apply_finding_suggestion(
    submission_id: str,
    payload: ApplySuggestionRequest,
    current_user: User = Depends(get_current_user),
):
    """Applies a suggestion to create a new revision without overwriting original content."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    finding = await Finding.get(payload.finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    latest_rev = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("-revision_number").first_or_none()

    if not latest_rev:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submission has no revisions",
        )

    current_text = latest_rev.extracted_text or latest_rev.raw_content or ""
    updated_text = current_text
    sugg = finding.suggestion or {}

    # Perform intent-preserving replacement
    action = sugg.get("action")
    if action in ("REPLACE_TERM", "REMOVE_TERM"):
        orig = sugg.get("original")
        replacement = sugg.get("replacement", "")
        if orig:
            pattern = re.compile(re.escape(orig), re.IGNORECASE)
            updated_text = pattern.sub(replacement, current_text, count=1)
    elif action == "ALIGN_WITH_APPROVED_FACT":
        metric = finding.evidence.get("found_value") if finding.evidence else None
        approved = sugg.get("approved_value")
        if metric and approved:
            updated_text = current_text.replace(str(metric), str(approved))
        elif sugg.get("statement"):
            updated_text = f"{current_text}\n{sugg.get('statement')}"
    elif action == "REWRITE_CLAIM":
        orig = sugg.get("original")
        suggested_corr = sugg.get("suggested_text")
        if orig and suggested_corr:
            updated_text = current_text.replace(orig, suggested_corr)

    next_rev_num = latest_rev.revision_number + 1

    # Store updated file bytes
    content_bytes = updated_text.encode("utf-8")
    storage_meta = storage_service.save_file(
        workspace_id=submission.workspace_id,
        filename=f"{submission.title}_rev{next_rev_num}.txt",
        content=content_bytes,
    )

    # Process Privacy Gate
    privacy_report = privacy_service.process(
        raw_text=updated_text,
        confidential_terms=[],
    )

    new_revision = SubmissionRevision(
        submission_id=submission.id,
        revision_number=next_rev_num,
        storage_key=storage_meta["storage_key"],
        content_hash=storage_meta["content_hash"],
        extracted_text=updated_text,
        sanitized_text=privacy_report["sanitized_text"],
        privacy_gate_metadata=privacy_report,
        raw_content=updated_text,
        created_by=current_user.id,
    )
    await new_revision.insert()

    # Mark finding as resolved
    finding.status = "RESOLVED"
    await finding.save()

    # Record Audit Event
    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="SUBMISSION_REVISION",
        entity_id=new_revision.id,
        action="SUGGESTION_APPLIED",
        metadata_json={
            "submission_id": submission.id,
            "revision_number": next_rev_num,
            "resolved_finding_id": finding.id,
            "finding_category": finding.category,
        },
    )

    # Automatically trigger audit on the new revision
    audit_run, findings = await deterministic_engine.run_audit(
        submission=submission,
        revision=new_revision,
    )
    final_score = compute_readiness_score(findings)
    audit_run.readiness_score = final_score
    await audit_run.save()

    audit_run_res = await build_audit_run_response(audit_run)
    finding_res_list = [await build_finding_response(f) for f in findings]

    return {
        "status": "success",
        "message": f"Suggestion applied. Incremental revision v{next_rev_num} created.",
        "new_revision": to_revision_response(new_revision),
        "audit_run": audit_run_res,
        "findings": finding_res_list,
    }


# --- 8. Request Exception Endpoints ---

@router.post(
    "/findings/{finding_id}/exceptions",
    response_model=ExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a human-in-the-loop exception request with business justification",
)
async def request_finding_exception(
    finding_id: str,
    payload: ExceptionCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """Submits an exception request for reviewer sign-off without silently overriding rules."""
    finding = await Finding.get(finding_id)
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found",
        )

    audit_run = await AuditRun.get(finding.audit_run_id)
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated audit run not found",
        )

    submission = await Submission.get(audit_run.submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated submission not found",
        )

    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    # Create ExceptionRequest
    exc = ExceptionRequest(
        finding_id=finding.id,
        submission_id=submission.id,
        requested_by=current_user.id,
        reason=payload.reason,
        status="PENDING",
    )
    await exc.insert()

    # Update Finding status to indicate exception is pending
    finding.status = "EXCEPTION_REQUESTED"
    await finding.save()

    # Record Audit Event
    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="EXCEPTION_REQUEST",
        entity_id=exc.id,
        action="EXCEPTION_REQUESTED",
        metadata_json={
            "submission_id": submission.id,
            "finding_id": finding.id,
            "reason": payload.reason,
        },
    )

    return ExceptionResponse(
        id=exc.id,
        finding_id=exc.finding_id,
        submission_id=exc.submission_id,
        requested_by=exc.requested_by,
        reason=exc.reason,
        status=exc.status,
        created_at=exc.created_at,
    )


@router.get(
    "/submissions/{submission_id}/exceptions",
    response_model=List[ExceptionResponse],
    summary="List all exception requests for a submission",
)
async def list_submission_exceptions(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lists all exception requests for reviewer inspection."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    membership = await Membership.find_one(
        Membership.workspace_id == submission.workspace_id,
        Membership.user_id == current_user.id,
    )
    if not membership and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden",
        )

    exceptions = await ExceptionRequest.find(
        ExceptionRequest.submission_id == submission.id
    ).to_list()

    return [
        ExceptionResponse(
            id=e.id,
            finding_id=e.finding_id,
            submission_id=e.submission_id,
            requested_by=e.requested_by,
            reason=e.reason,
            status=e.status,
            created_at=e.created_at,
        )
        for e in exceptions
    ]
