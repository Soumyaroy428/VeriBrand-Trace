"""Batch Audit Processing Service.

Coordinates bulk content auditing for multi-asset marketing campaigns:
- Parallel or sequential item orchestration through Privacy Gate, Deterministic Engine, and RAG verification.
- Aggregation of campaign-wide compliance score, risk distribution, and executive verdict.
- Cryptographic SHA-256 audit trail chaining.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

from app.models.base import utc_now
from app.models.documents import (
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    FindingEvidence,
    AuditEvent,
    BatchAudit,
)
from app.schemas.batches import (
    BatchItemCreate,
    BatchItemSummary,
    BatchExportReport,
)
from app.services.privacy import privacy_service
from app.services.deterministic_engine import deterministic_engine
from app.services.rag_engine import rag_engine
from app.services.ai_claim_verifier import ai_claim_verifier

logger = logging.getLogger("uvicorn")


class BatchProcessorService:
    """Service for managing, running, and analyzing multi-asset campaign batch audits."""

    async def create_batch(
        self,
        workspace_id: str,
        user_id: str,
        title: str,
        campaign_tag: Optional[str],
        items: List[BatchItemCreate],
    ) -> BatchAudit:
        """Initializes a new batch audit, creating individual submissions and initial revisions."""
        import hashlib
        submission_ids: List[str] = []

        for item in items:
            # 1. Create Submission Document
            submission = Submission(
                workspace_id=workspace_id,
                title=item.title,
                input_type="TEXT",
                created_by=user_id,
                status="DRAFT",
            )
            await submission.insert()

            # 2. Run Privacy Scrubbing Gate
            scrub_result = privacy_service.process(
                raw_text=item.content,
            )

            # 3. Create Revision 1
            content_bytes = item.content.encode("utf-8")
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            revision = SubmissionRevision(
                submission_id=submission.id,
                revision_number=1,
                content_hash=content_hash,
                raw_content=item.content,
                extracted_text=item.content,
                sanitized_text=scrub_result["sanitized_text"],
                privacy_gate_metadata=scrub_result,
                created_by=user_id,
            )
            await revision.insert()

            submission_ids.append(submission.id)

        # 4. Create and persist BatchAudit
        batch = BatchAudit(
            workspace_id=workspace_id,
            title=title,
            campaign_tag=campaign_tag,
            created_by=user_id,
            status="PENDING",
            submission_ids=submission_ids,
            total_items=len(submission_ids),
            completed_items=0,
            aggregate_score=0.0,
            critical_violations=0,
            warning_violations=0,
            info_violations=0,
            campaign_rating="PENDING_AUDIT",
        )
        await batch.insert()

        # 5. Record Cryptographic Audit Event
        await self._record_audit_event(
            workspace_id=workspace_id,
            actor_user_id=user_id,
            entity_type="BATCH_AUDIT",
            entity_id=batch.id,
            action="BATCH_CREATED",
            metadata_json={
                "batch_id": batch.id,
                "title": title,
                "campaign_tag": campaign_tag,
                "total_items": len(submission_ids),
            },
        )

        return batch

    async def execute_batch(
        self,
        batch: BatchAudit,
        actor_user_id: str,
    ) -> BatchAudit:
        """Executes full compliance audit across all submissions in the batch."""
        batch.status = "PROCESSING"
        batch.updated_at = utc_now()
        await batch.save()

        scores: List[float] = []
        total_crit = 0
        total_warn = 0
        total_info = 0
        completed_count = 0

        for sub_id in batch.submission_ids:
            submission = await Submission.get(sub_id)
            if not submission:
                continue

            latest_rev = await SubmissionRevision.find(
                SubmissionRevision.submission_id == sub_id
            ).sort("-revision_number").first_or_none()

            if not latest_rev:
                continue

            # 1. Deterministic Engine
            audit_run, findings = await deterministic_engine.run_audit(
                submission=submission,
                revision=latest_rev,
            )

            # 2. RAG Evidence Retrieval
            text_to_audit = latest_rev.sanitized_text or latest_rev.extracted_text or latest_rev.raw_content or ""
            evidence_passages = await rag_engine.retrieve_evidence(
                workspace_id=submission.workspace_id,
                query=text_to_audit,
                top_k=5,
            )

            # 3. Grounded AI Claim & Tone Verification
            ai_findings_raw, _, _ = await ai_claim_verifier.verify_claims(
                sanitized_text=text_to_audit,
                retrieved_evidence=evidence_passages,
                workspace_id=submission.workspace_id,
            )

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

                if ai_f.retrieved_evidence_quote or ai_f.source_citation:
                    ev_doc = FindingEvidence(
                        finding_id=finding_doc.id,
                        source_type="GUIDELINE_CHUNK" if "guideline" in (ai_f.source_citation or "").lower() else "APPROVED_FACT",
                        source_version=1,
                        quote=ai_f.retrieved_evidence_quote or "Brand Vault reference passage.",
                        location=ai_f.source_citation or "Brand Vault",
                    )
                    await ev_doc.insert()

            # Tally findings for this run
            all_findings = await Finding.find(Finding.audit_run_id == audit_run.id).to_list()
            crit = sum(1 for f in all_findings if f.severity == "CRITICAL")
            high = sum(1 for f in all_findings if f.severity == "HIGH")
            med = sum(1 for f in all_findings if f.severity == "MEDIUM")
            low = sum(1 for f in all_findings if f.severity == "LOW")

            total_crit += crit
            total_warn += (high + med)
            total_info += low

            scores.append(audit_run.readiness_score)
            completed_count += 1

            submission.status = "AUDITED"
            submission.updated_at = utc_now()
            await submission.save()

        # Compute aggregate metrics
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        if total_crit == 0 and avg_score >= 85.0:
            rating = "CAMPAIGN_READY"
        elif total_crit == 0 and avg_score >= 70.0:
            rating = "REQUIRES_REMEDIATION"
        else:
            rating = "CRITICAL_RISK"

        batch.status = "COMPLETED"
        batch.completed_items = completed_count
        batch.aggregate_score = avg_score
        batch.critical_violations = total_crit
        batch.warning_violations = total_warn
        batch.info_violations = total_info
        batch.campaign_rating = rating
        batch.updated_at = utc_now()
        await batch.save()

        # Record Completion in Tamper-Evident Ledger
        await self._record_audit_event(
            workspace_id=batch.workspace_id,
            actor_user_id=actor_user_id,
            entity_type="BATCH_AUDIT",
            entity_id=batch.id,
            action="BATCH_AUDITED",
            metadata_json={
                "batch_id": batch.id,
                "aggregate_score": avg_score,
                "campaign_rating": rating,
                "completed_items": completed_count,
                "critical_violations": total_crit,
                "warning_violations": total_warn,
            },
        )

        return batch

    async def get_batch_items_summary(self, batch: BatchAudit) -> List[BatchItemSummary]:
        """Collects item-level summary cards for UI and executive breakdown."""
        summaries: List[BatchItemSummary] = []

        for sub_id in batch.submission_ids:
            sub = await Submission.get(sub_id)
            if not sub:
                continue

            latest_run = await AuditRun.find(
                AuditRun.submission_id == sub_id
            ).sort("-created_at").first_or_none()

            crit = high = med = low = total = 0
            score = 0.0

            if latest_run:
                score = latest_run.readiness_score
                findings = await Finding.find(Finding.audit_run_id == latest_run.id).to_list()
                total = len(findings)
                crit = sum(1 for f in findings if f.severity == "CRITICAL")
                high = sum(1 for f in findings if f.severity == "HIGH")
                med = sum(1 for f in findings if f.severity == "MEDIUM")
                low = sum(1 for f in findings if f.severity == "LOW")

            summaries.append(
                BatchItemSummary(
                    submission_id=sub.id,
                    title=sub.title,
                    status=sub.status,
                    readiness_score=score,
                    critical_findings=crit,
                    high_findings=high,
                    medium_findings=med,
                    low_findings=low,
                    total_findings=total,
                )
            )

        return summaries

    async def export_batch_report(self, batch: BatchAudit) -> BatchExportReport:
        """Assembles executive-level campaign governance report."""
        item_summaries = await self.get_batch_items_summary(batch)

        items_data = [
            {
                "submission_id": item.submission_id,
                "title": item.title,
                "status": item.status,
                "readiness_score": item.readiness_score,
                "critical_findings": item.critical_findings,
                "warning_findings": item.high_findings + item.medium_findings,
                "info_findings": item.low_findings,
                "total_findings": item.total_findings,
            }
            for item in item_summaries
        ]

        return BatchExportReport(
            batch_id=batch.id,
            workspace_id=batch.workspace_id,
            title=batch.title,
            campaign_tag=batch.campaign_tag,
            aggregate_score=batch.aggregate_score,
            campaign_rating=batch.campaign_rating,
            total_items=batch.total_items,
            completed_items=batch.completed_items,
            critical_violations=batch.critical_violations,
            warning_violations=batch.warning_violations,
            generated_at=utc_now().isoformat(),
            items=items_data,
        )

    async def _record_audit_event(
        self,
        workspace_id: str,
        actor_user_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        metadata_json: dict,
    ) -> AuditEvent:
        """Chains cryptographic SHA-256 event for tamper-evident ledger tracking."""
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


batch_processor = BatchProcessorService()
