"""Submissions & Privacy Gate API Endpoints.

Handles:
- Content submission uploads (TXT, DOCX, PDF, PNG, JPG) and direct text submissions.
- Strict binary signature (magic bytes) validation and file size restrictions.
- Immutable file storage with SHA-256 content hashing.
- Text extraction and image processing.
- Privacy Gate PII scrubbing and confidential project terms masking.
- Cryptographic SHA-256 chained audit trail.
- Workspace-isolated retrieval and role-based access control.
"""

import io
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import (
    APIRouter,
    Request,
    HTTPException,
    status,
    Depends,
    Query,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import Response

from app.core.dependencies import get_current_user, require_workspace_role
from app.models.documents import (
    User,
    Membership,
    Submission,
    SubmissionRevision,
    AuditEvent,
)
from app.schemas.submissions import (
    ContentSubmissionCreate,
    SubmissionRevisionCreate,
    SubmissionResponse,
    SubmissionListResponse,
    SubmissionDetailResponse,
    SubmissionRevisionResponse,
)
from app.services.storage import storage_service
from app.services.extractor import extraction_service
from app.services.privacy import privacy_service

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

    audit_entry = AuditEvent(
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
    await audit_entry.insert()
    return audit_entry


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


def to_submission_response(sub: Submission, latest_rev: Optional[SubmissionRevision] = None) -> SubmissionResponse:
    """Converts Submission document to response schema."""
    return SubmissionResponse(
        id=sub.id,
        workspace_id=sub.workspace_id,
        created_by=sub.created_by,
        title=sub.title,
        input_type=sub.input_type,
        status=sub.status,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        latest_revision=to_revision_response(latest_rev) if latest_rev else None,
    )


# --- 1. Submission Creation (JSON or Multipart Form) ---

@router.post(
    "/workspaces/{workspace_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create content submission with Privacy Gate validation",
)
async def create_submission(
    workspace_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_workspace_role(["CREATOR", "REVIEWER", "GOVERNANCE_ADMIN"])),
):
    """Creates a submission, extracts content, and processes Privacy Gate."""
    content_type = request.headers.get("content-type", "")

    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    title: str = ""
    confidential_terms: List[str] = []
    text_content: Optional[str] = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        uploaded_file = form.get("file")
        title = form.get("title", "")
        raw_terms = form.get("confidential_terms", "")
        text_content = form.get("text_content")

        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title is required for submission",
            )

        if raw_terms:
            try:
                confidential_terms = json.loads(raw_terms) if raw_terms.startswith("[") else [t.strip() for t in raw_terms.split(",") if t.strip()]
            except Exception:
                confidential_terms = [t.strip() for t in raw_terms.split(",") if t.strip()]

        if uploaded_file and hasattr(uploaded_file, "read"):
            filename = uploaded_file.filename
            file_bytes = await uploaded_file.read()
    else:
        # JSON body payload
        try:
            body = await request.json()
            payload = ContentSubmissionCreate(**body)
            title = payload.title
            text_content = payload.text_content
            confidential_terms = payload.confidential_terms or []
            filename = f"{title}.txt"
            file_bytes = text_content.encode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON submission body: {str(e)}",
            )

    if not file_bytes and not text_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a document/image file or text_content must be provided",
        )

    # 1. Validate and Store File
    try:
        storage_meta = storage_service.save_file(
            workspace_id=workspace_id,
            filename=filename or "content.txt",
            content=file_bytes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File validation failed: {str(e)}",
        )

    # 2. Extract Text & Structure
    try:
        extraction_res = extraction_service.extract(
            input_type=storage_meta["input_type"],
            content=file_bytes,
            filename=filename,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Content extraction failed: {str(e)}",
        )

    raw_extracted_text = extraction_res["text"]

    # 3. Process Privacy Gate (PII Scrubbing & Project Masking)
    privacy_report = privacy_service.process(
        raw_text=raw_extracted_text,
        confidential_terms=confidential_terms,
    )

    # 4. Save Submission
    submission = Submission(
        workspace_id=workspace_id,
        created_by=current_user.id,
        title=title,
        input_type=storage_meta["input_type"],
        status="DRAFT",
    )
    await submission.insert()

    # 5. Save Immutable Revision 1
    revision = SubmissionRevision(
        submission_id=submission.id,
        revision_number=1,
        storage_key=storage_meta["storage_key"],
        content_hash=storage_meta["content_hash"],
        extracted_text=raw_extracted_text,
        sanitized_text=privacy_report["sanitized_text"],
        privacy_gate_metadata=privacy_report,
        raw_content=text_content or raw_extracted_text,
        created_by=current_user.id,
    )
    await revision.insert()

    # 6. Record Audit Event
    await record_audit_event(
        workspace_id=workspace_id,
        actor_user_id=current_user.id,
        entity_type="SUBMISSION",
        entity_id=submission.id,
        action="SUBMISSION_CREATED",
        metadata_json={
            "revision_number": 1,
            "input_type": storage_meta["input_type"],
            "privacy_status": privacy_report["status"],
            "pii_count": len(privacy_report["pii_detected"]),
            "confidential_terms_count": len(privacy_report["confidential_terms_masked"]),
            "content_hash": storage_meta["content_hash"],
        },
    )

    return to_submission_response(submission, revision)


# --- 2. List Submissions in Workspace ---

@router.get(
    "/workspaces/{workspace_id}/submissions",
    response_model=SubmissionListResponse,
    summary="List all submissions for a workspace",
)
async def list_workspace_submissions(
    workspace_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(require_workspace_role(["CREATOR", "REVIEWER", "GOVERNANCE_ADMIN"])),
):
    """Lists submissions in workspace with pagination and attaches latest revision."""
    query = Submission.workspace_id == workspace_id
    if status_filter:
        query = (query) & (Submission.status == status_filter)

    submissions = await Submission.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    total = await Submission.find(query).count()

    result = []
    for sub in submissions:
        latest_rev = await SubmissionRevision.find(
            SubmissionRevision.submission_id == sub.id
        ).sort("-revision_number").first_or_none()
        result.append(to_submission_response(sub, latest_rev))

    return SubmissionListResponse(submissions=result, total=total)


# --- 3. Get Submission Detail ---

@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionDetailResponse,
    summary="Get submission details with revision history",
)
async def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves submission detail ensuring user is a member of the workspace."""
    submission = await Submission.get(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found",
        )

    # Verify workspace membership
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

    latest_rev = revisions[-1] if revisions else None
    rev_responses = [to_revision_response(r) for r in revisions]

    return SubmissionDetailResponse(
        submission=to_submission_response(submission, latest_rev),
        revisions=rev_responses,
    )


# --- 4. Get Revisions List ---

@router.get(
    "/submissions/{submission_id}/revisions",
    response_model=List[SubmissionRevisionResponse],
    summary="Get all revisions for a submission",
)
async def list_submission_revisions(
    submission_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lists all revisions for a submission."""
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

    revisions = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("revision_number").to_list()

    return [to_revision_response(r) for r in revisions]


# --- 5. Create Edited Revision ---

@router.post(
    "/submissions/{submission_id}/revisions",
    response_model=SubmissionRevisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an updated content revision to an existing submission",
)
async def create_submission_revision(
    submission_id: str,
    payload: SubmissionRevisionCreate,
    current_user: User = Depends(get_current_user),
):
    """Creates an incremental revision (v2, v3) with Privacy Gate validation."""
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

    # Determine next revision number
    latest_rev = await SubmissionRevision.find(
        SubmissionRevision.submission_id == submission.id
    ).sort("-revision_number").first_or_none()
    next_rev_num = (latest_rev.revision_number + 1) if latest_rev else 1

    # Store content
    content_bytes = payload.raw_content.encode("utf-8")
    storage_meta = storage_service.save_file(
        workspace_id=submission.workspace_id,
        filename=f"{submission.title}_rev{next_rev_num}.txt",
        content=content_bytes,
    )

    # Process Privacy Gate
    privacy_report = privacy_service.process(
        raw_text=payload.raw_content,
        confidential_terms=payload.confidential_terms,
    )

    revision = SubmissionRevision(
        submission_id=submission.id,
        revision_number=next_rev_num,
        storage_key=storage_meta["storage_key"],
        content_hash=storage_meta["content_hash"],
        extracted_text=payload.raw_content,
        sanitized_text=privacy_report["sanitized_text"],
        privacy_gate_metadata=privacy_report,
        raw_content=payload.raw_content,
        created_by=current_user.id,
    )
    await revision.insert()

    # Update submission timestamp and reset status if needed
    submission.updated_at = datetime.now(timezone.utc)
    if submission.status == "NEEDS_CHANGES":
        submission.status = "DRAFT"
    await submission.save()

    # Record Audit Event
    await record_audit_event(
        workspace_id=submission.workspace_id,
        actor_user_id=current_user.id,
        entity_type="SUBMISSION_REVISION",
        entity_id=revision.id,
        action="SUBMISSION_REVISION_CREATED",
        metadata_json={
            "submission_id": submission.id,
            "revision_number": next_rev_num,
            "privacy_status": privacy_report["status"],
            "content_hash": storage_meta["content_hash"],
        },
    )

    return to_revision_response(revision)


# --- 6. Retrieve Stored Original File Bytes ---

@router.get(
    "/submissions/{submission_id}/revisions/{revision_id}/file",
    summary="Download the raw immutable file for a submission revision",
)
async def download_revision_file(
    submission_id: str,
    revision_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieves original immutable file content with integrity verification."""
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

    revision = await SubmissionRevision.get(revision_id)
    if not revision or revision.submission_id != submission.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Revision not found",
        )

    if not revision.storage_key:
        # If text content without explicit storage_key
        return Response(
            content=revision.raw_content or revision.extracted_text or "",
            media_type="text/plain; charset=utf-8",
        )

    try:
        content_bytes = storage_service.get_file_bytes(revision.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Underlying stored file not found",
        )

    return Response(
        content=content_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="submission_{submission.id}_v{revision.revision_number}"',
            "ETag": f'"{revision.content_hash}"',
        },
    )

