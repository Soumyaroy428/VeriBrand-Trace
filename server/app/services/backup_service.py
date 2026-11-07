"""Disaster Recovery and Cryptographic Backup Service.

Creates cryptographically signed, complete workspace exports for auditing,
disaster recovery, and regulatory compliance.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any

from app.models.base import utc_now
from app.models.documents import (
    Workspace,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    GuidelineDocument,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    ComplianceCertificate,
    AuditEvent,
)
from app.schemas.operations import WorkspaceBackupResponse
from app.services.audit_verifier import record_audit_event


class BackupService:
    """Handles workspace data backup, cryptographic sealing, and disaster recovery exports."""

    async def create_workspace_backup(
        self,
        workspace_id: str,
        actor_user_id: str,
    ) -> WorkspaceBackupResponse:
        """Assembles a sealed backup manifest of all brand governance assets and audit ledgers."""
        ws = await Workspace.get(workspace_id)
        ws_name = ws.name if ws else "Unknown Workspace"

        # 1. Collect all workspace entities
        facts = await ApprovedFact.find(ApprovedFact.workspace_id == workspace_id).to_list()
        terms = await TerminologyRule.find(TerminologyRule.workspace_id == workspace_id).to_list()
        visuals = await VisualRule.find(VisualRule.workspace_id == workspace_id).to_list()
        guidelines = await GuidelineDocument.find(GuidelineDocument.workspace_id == workspace_id).to_list()
        submissions = await Submission.find(Submission.workspace_id == workspace_id).to_list()
        certificates = await ComplianceCertificate.find(ComplianceCertificate.workspace_id == workspace_id).to_list()
        events = await AuditEvent.find(AuditEvent.workspace_id == workspace_id).sort("created_at").to_list()

        # Collect revisions and findings associated with these submissions
        sub_ids = [s.id for s in submissions]
        revisions = await SubmissionRevision.find(
            {"submission_id": {"$in": sub_ids}}
        ).to_list() if sub_ids else []

        audit_runs = await AuditRun.find(
            {"submission_id": {"$in": sub_ids}}
        ).to_list() if sub_ids else []

        run_ids = [r.id for r in audit_runs]
        findings = await Finding.find(
            {"audit_run_id": {"$in": run_ids}}
        ).to_list() if run_ids else []

        # 2. Serialize Payload
        payload: Dict[str, Any] = {
            "workspace": ws.model_dump() if ws else {},
            "guideline_documents": [g.model_dump() for g in guidelines],
            "approved_facts": [f.model_dump() for f in facts],
            "terminology_rules": [t.model_dump() for t in terms],
            "visual_rules": [v.model_dump() for v in visuals],
            "submissions": [s.model_dump() for s in submissions],
            "submission_revisions": [r.model_dump() for r in revisions],
            "audit_runs": [ar.model_dump() for ar in audit_runs],
            "findings": [f.model_dump() for f in findings],
            "compliance_certificates": [c.model_dump() for c in certificates],
            "audit_ledger_events": [e.model_dump() for e in events],
        }

        # 3. Compute Cryptographic SHA-256 Seal
        serialized = json.dumps(payload, sort_keys=True, default=str)
        seal_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        # 4. Count Summary
        entities_count = {
            "guideline_documents": len(guidelines),
            "approved_facts": len(facts),
            "terminology_rules": len(terms),
            "visual_rules": len(visuals),
            "submissions": len(submissions),
            "submission_revisions": len(revisions),
            "audit_runs": len(audit_runs),
            "findings": len(findings),
            "compliance_certificates": len(certificates),
            "audit_ledger_events": len(events),
        }

        # 5. Log in cryptographic chain
        await record_audit_event(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            entity_type="SYSTEM_BACKUP",
            entity_id=seal_sha256[:16],
            action="WORKSPACE_BACKUP_CREATED",
            metadata_json={"seal": seal_sha256, "entities": entities_count},
        )

        return WorkspaceBackupResponse(
            workspace_id=workspace_id,
            workspace_name=ws_name,
            backup_timestamp=utc_now().isoformat(),
            backup_seal_sha256=seal_sha256,
            entities_backed_up=entities_count,
            payload=payload,
        )


backup_service = BackupService()
