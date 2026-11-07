"""Cryptographic Audit Trail & Tamper-Evident Ledger Verification Service.

Implements sequential SHA-256 hash chaining verification for multi-tenant workspace
audit events. Accurately detects data tampering, event deletions, out-of-order mutations,
or payload alterations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.models.documents import AuditEvent, User, Workspace
from app.models.base import utc_now


class CorruptedEventDetail(BaseModel):
    event_id: str
    action: str
    created_at: datetime
    reason: str
    expected_hash: Optional[str] = None
    actual_hash: str
    previous_hash: Optional[str] = None


class AuditChainVerificationReport(BaseModel):
    is_valid: bool
    status: str  # "VERIFIED_INTACT" | "TAMPERING_DETECTED" | "EMPTY_LEDGER"
    workspace_id: str
    total_events: int
    verified_events: int
    corrupted_count: int
    corrupted_events: List[CorruptedEventDetail]
    genesis_hash: Optional[str] = None
    latest_hash: Optional[str] = None
    verified_at: datetime


async def record_audit_event(
    workspace_id: str,
    actor_user_id: Optional[str],
    entity_type: str,
    entity_id: str,
    action: str,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Appends an immutable, cryptographically SHA-256 chained audit event to the workspace ledger."""
    created_at_now = utc_now()
    created_at_iso = created_at_now.isoformat()

    # Find the most recent audit event in this workspace to chain the previous hash
    existing_events = await AuditEvent.find(
        AuditEvent.workspace_id == workspace_id
    ).to_list()
    last_event = existing_events[-1] if existing_events else None
    previous_hash = last_event.event_hash if last_event else None

    # Preserve exact ISO timestamp in metadata for byte-for-byte reproducibility
    meta = dict(metadata_json) if metadata_json else {}
    meta["_created_at_iso"] = created_at_iso

    event_hash = AuditEvent.calculate_hash(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata_json=meta,
        previous_hash=previous_hash,
        created_at_iso=created_at_iso,
    )

    audit_entry = AuditEvent(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata_json=meta,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at_now,
    )
    await audit_entry.insert()
    return audit_entry


async def verify_workspace_audit_chain(workspace_id: str) -> AuditChainVerificationReport:
    """Performs rigorous, mathematical SHA-256 chain verification for all events in a workspace."""
    now = utc_now()
    
    # Retrieve all audit events ordered chronologically from genesis to latest
    events = await AuditEvent.find(
        AuditEvent.workspace_id == workspace_id
    ).to_list()

    if not events:
        return AuditChainVerificationReport(
            is_valid=True,
            status="EMPTY_LEDGER",
            workspace_id=workspace_id,
            total_events=0,
            verified_events=0,
            corrupted_count=0,
            corrupted_events=[],
            genesis_hash=None,
            latest_hash=None,
            verified_at=now,
        )

    expected_prev_hash: Optional[str] = None
    corrupted: List[CorruptedEventDetail] = []
    verified_count = 0

    for idx, event in enumerate(events):
        event_corrupted = False
        meta = event.metadata_json or {}
        created_iso = meta.get("_created_at_iso") or event.created_at.isoformat()

        # Check 1: Previous hash link integrity
        if idx == 0:
            if event.previous_hash is not None and event.previous_hash != "":
                corrupted.append(
                    CorruptedEventDetail(
                        event_id=event.id,
                        action=event.action,
                        created_at=event.created_at,
                        reason="Genesis event must have null previous_hash",
                        expected_hash=None,
                        actual_hash=event.event_hash,
                        previous_hash=event.previous_hash,
                    )
                )
                event_corrupted = True
        else:
            if event.previous_hash != expected_prev_hash:
                corrupted.append(
                    CorruptedEventDetail(
                        event_id=event.id,
                        action=event.action,
                        created_at=event.created_at,
                        reason=f"Broken chain link: previous_hash '{event.previous_hash}' does not match prior event hash '{expected_prev_hash}'",
                        expected_hash=expected_prev_hash,
                        actual_hash=event.event_hash,
                        previous_hash=event.previous_hash,
                    )
                )
                event_corrupted = True

        # Check 2: Re-compute deterministic SHA-256 hash of payload
        recomputed_hash = AuditEvent.calculate_hash(
            workspace_id=event.workspace_id,
            actor_user_id=event.actor_user_id,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            action=event.action,
            metadata_json=event.metadata_json,
            previous_hash=event.previous_hash,
            created_at_iso=created_iso,
        )

        if recomputed_hash != event.event_hash:
            corrupted.append(
                CorruptedEventDetail(
                    event_id=event.id,
                    action=event.action,
                    created_at=event.created_at,
                    reason=f"Payload altered: recomputed hash '{recomputed_hash}' does not match stored hash '{event.event_hash}'",
                    expected_hash=recomputed_hash,
                    actual_hash=event.event_hash,
                    previous_hash=event.previous_hash,
                )
            )
            event_corrupted = True

        if not event_corrupted:
            verified_count += 1

        # Advance pointer
        expected_prev_hash = event.event_hash

    is_valid = (len(corrupted) == 0)
    status_label = "VERIFIED_INTACT" if is_valid else "TAMPERING_DETECTED"

    return AuditChainVerificationReport(
        is_valid=is_valid,
        status=status_label,
        workspace_id=workspace_id,
        total_events=len(events),
        verified_events=verified_count,
        corrupted_count=len(corrupted),
        corrupted_events=corrupted,
        genesis_hash=events[0].event_hash if events else None,
        latest_hash=events[-1].event_hash if events else None,
        verified_at=now,
    )
