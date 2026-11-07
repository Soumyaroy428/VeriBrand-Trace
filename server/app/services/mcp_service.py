"""Model Context Protocol (MCP) Service.

Implements safe, workspace-scoped brand governance tools for AI agents and IDEs.
Adheres strictly to the core safety rule: "Suggest, Never Override".
MCP tools can retrieve rules, audit text, and request exceptions, but CANNOT
grant final approval or publish content.
"""

import hashlib
from typing import Dict, Any, List, Optional

from app.models.base import utc_now
from app.models.documents import (
    Workspace,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    Submission,
    SubmissionRevision,
    AuditRun,
    Finding,
    FindingEvidence,
    ExceptionRequest,
    ComplianceCertificate,
)
from app.schemas.mcp import (
    MCPToolDefinition,
    MCPToolParameter,
    MCPToolCallResponse,
)
from app.services.deterministic_engine import deterministic_engine
from app.services.rag_engine import rag_engine
from app.services.ai_claim_verifier import ai_claim_verifier
from app.services.privacy import privacy_service
from app.services.audit_verifier import record_audit_event


AVAILABLE_MCP_TOOLS: List[MCPToolDefinition] = [
    MCPToolDefinition(
        name="get_brand_rules",
        description="Retrieve active brand terminology rules and visual guidelines for the workspace.",
        parameters=[],
        required_role="CREATOR",
    ),
    MCPToolDefinition(
        name="search_approved_facts",
        description="Search verified claims and approved numeric facts in the workspace Fact Registry.",
        parameters=[
            MCPToolParameter(name="query", type="string", description="Search query or keyword", required=False),
        ],
        required_role="CREATOR",
    ),
    MCPToolDefinition(
        name="audit_text",
        description="Submit marketing copy or draft text for brand governance verification. Returns readiness score and violation cards.",
        parameters=[
            MCPToolParameter(name="title", type="string", description="Title of the content", required=True),
            MCPToolParameter(name="text", type="string", description="Plaintext content to audit", required=True),
        ],
        required_role="CREATOR",
    ),
    MCPToolDefinition(
        name="get_audit_findings",
        description="Retrieve detailed violation cards and evidence citations for a completed audit run.",
        parameters=[
            MCPToolParameter(name="audit_run_id", type="string", description="ID of the audit run", required=True),
        ],
        required_role="CREATOR",
    ),
    MCPToolDefinition(
        name="request_exception",
        description="Submit a justified exception request for an intentional brand deviation.",
        parameters=[
            MCPToolParameter(name="finding_id", type="string", description="ID of the violation finding", required=True),
            MCPToolParameter(name="rationale", type="string", description="Business justification for the exception", required=True),
        ],
        required_role="CREATOR",
    ),
    MCPToolDefinition(
        name="get_review_status",
        description="Inspect human reviewer approval status and compliance certificate number.",
        parameters=[
            MCPToolParameter(name="submission_id", type="string", description="ID of the submission", required=True),
        ],
        required_role="CREATOR",
    ),
]


class MCPService:
    """Service implementing Model Context Protocol brand governance tools."""

    def list_tools(self) -> List[MCPToolDefinition]:
        """Returns catalogue of accessible MCP tools."""
        return AVAILABLE_MCP_TOOLS

    async def execute_tool(
        self,
        workspace_id: str,
        user_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolCallResponse:
        """Executes an MCP tool with workspace isolation and human-in-the-loop safety checks."""
        # Safety Gate: Prevent unauthorized approval/publishing tools via MCP
        banned_mcp_actions = ["approve_submission", "publish_content", "override_reviewer", "delete_audit_event"]
        if tool_name.lower() in banned_mcp_actions:
            return MCPToolCallResponse(
                tool=tool_name,
                success=False,
                error="MCP clients are restricted from granting final approval or publishing. Core Safety Rule: 'Suggest, Never Override'.",
            )

        try:
            if tool_name == "get_brand_rules":
                res = await self._get_brand_rules(workspace_id)
            elif tool_name == "search_approved_facts":
                res = await self._search_approved_facts(workspace_id, arguments.get("query", ""))
            elif tool_name == "audit_text":
                res = await self._audit_text(workspace_id, user_id, arguments.get("title", "MCP Draft"), arguments.get("text", ""))
            elif tool_name == "get_audit_findings":
                res = await self._get_audit_findings(workspace_id, arguments.get("audit_run_id", ""))
            elif tool_name == "request_exception":
                res = await self._request_exception(workspace_id, user_id, arguments.get("finding_id", ""), arguments.get("rationale", ""))
            elif tool_name == "get_review_status":
                res = await self._get_review_status(workspace_id, arguments.get("submission_id", ""))
            else:
                return MCPToolCallResponse(
                    tool=tool_name,
                    success=False,
                    error=f"Unknown MCP tool '{tool_name}'. Consult list_tools for available capabilities.",
                )

            # Record in cryptographic audit ledger
            audit_ev = await record_audit_event(
                workspace_id=workspace_id,
                actor_user_id=user_id,
                entity_type="MCP_TOOL",
                entity_id=tool_name,
                action="MCP_TOOL_INVOKED",
                metadata_json={"tool": tool_name, "arguments": arguments},
            )

            return MCPToolCallResponse(
                tool=tool_name,
                success=True,
                result=res,
                audit_event_id=audit_ev.id,
            )
        except Exception as exc:
            return MCPToolCallResponse(
                tool=tool_name,
                success=False,
                error=str(exc),
            )

    async def _get_brand_rules(self, workspace_id: str) -> Dict[str, Any]:
        """Retrieves active terminology rules and visual guidelines."""
        terms = await TerminologyRule.find(TerminologyRule.workspace_id == workspace_id).to_list()
        visuals = await VisualRule.find(VisualRule.workspace_id == workspace_id).to_list()
        return {
            "terminology_rules": [
                {
                    "term": t.term,
                    "rule_type": t.rule_type,
                    "replacement": t.replacement,
                }
                for t in terms
            ],
            "visual_rules": [
                {
                    "rule_name": v.rule_name,
                    "category": v.category,
                    "config": v.config,
                }
                for v in visuals
            ],
        }

    async def _search_approved_facts(self, workspace_id: str, query: str) -> Dict[str, Any]:
        """Searches approved facts matching query."""
        facts = await ApprovedFact.find(ApprovedFact.workspace_id == workspace_id).to_list()
        q_lower = query.lower().strip()
        matched = [
            {
                "fact_key": f.fact_key,
                "statement": f.statement,
                "source_reference": f.source_reference,
            }
            for f in facts
            if not q_lower or q_lower in f.statement.lower() or q_lower in f.fact_key.lower()
        ]
        return {"total_matches": len(matched), "facts": matched}

    async def _audit_text(self, workspace_id: str, user_id: str, title: str, text: str) -> Dict[str, Any]:
        """Executes full audit pipeline from MCP request."""
        # 1. Privacy Scrubbing
        scrub = privacy_service.process(raw_text=text)

        # 2. Create Submission & Revision
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        submission = Submission(
            workspace_id=workspace_id,
            title=title,
            input_type="TEXT",
            created_by=user_id,
            status="DRAFT",
        )
        await submission.insert()

        revision = SubmissionRevision(
            submission_id=submission.id,
            revision_number=1,
            content_hash=content_hash,
            raw_content=text,
            extracted_text=text,
            sanitized_text=scrub["sanitized_text"],
            privacy_gate_metadata=scrub,
            created_by=user_id,
        )
        await revision.insert()

        # 3. Deterministic Engine
        audit_run, findings = await deterministic_engine.run_audit(
            submission=submission,
            revision=revision,
        )

        # 4. RAG Evidence Retrieval
        evidence_passages = await rag_engine.retrieve_evidence(
            workspace_id=workspace_id,
            query=scrub["sanitized_text"],
            top_k=5,
        )

        # 5. AI Claim Verification
        ai_findings_raw, _, _ = await ai_claim_verifier.verify_claims(
            sanitized_text=scrub["sanitized_text"],
            retrieved_evidence=evidence_passages,
            workspace_id=workspace_id,
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
                },
                suggestion={
                    "action": "REWRITE_CLAIM",
                    "original": ai_f.claim_text,
                    "suggested_text": ai_f.suggested_correction,
                } if ai_f.suggested_correction else None,
                status="OPEN",
            )
            await finding_doc.insert()

        all_findings = await Finding.find(Finding.audit_run_id == audit_run.id).to_list()

        return {
            "submission_id": submission.id,
            "audit_run_id": audit_run.id,
            "readiness_score": audit_run.readiness_score,
            "status": audit_run.status,
            "total_findings": len(all_findings),
            "findings": [
                {
                    "id": f.id,
                    "category": f.category,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "suggestion": f.suggestion,
                }
                for f in all_findings
            ],
        }

    async def _get_audit_findings(self, workspace_id: str, audit_run_id: str) -> Dict[str, Any]:
        """Retrieves findings for a specific audit run."""
        audit_run = await AuditRun.get(audit_run_id)
        if not audit_run:
            raise ValueError(f"Audit run '{audit_run_id}' not found.")

        findings = await Finding.find(Finding.audit_run_id == audit_run_id).to_list()
        return {
            "audit_run_id": audit_run.id,
            "readiness_score": audit_run.readiness_score,
            "total_findings": len(findings),
            "findings": [
                {
                    "id": f.id,
                    "category": f.category,
                    "severity": f.severity,
                    "source_engine": f.source_engine,
                    "title": f.title,
                    "description": f.description,
                    "suggestion": f.suggestion,
                }
                for f in findings
            ],
        }

    async def _request_exception(self, workspace_id: str, user_id: str, finding_id: str, rationale: str) -> Dict[str, Any]:
        """Creates an exception request for a finding."""
        finding = await Finding.get(finding_id)
        if not finding:
            raise ValueError(f"Finding '{finding_id}' not found.")

        audit_run = await AuditRun.get(finding.audit_run_id)
        if not audit_run:
            raise ValueError("Associated audit run not found.")

        req = ExceptionRequest(
            finding_id=finding.id,
            submission_id=audit_run.submission_id,
            requested_by=user_id,
            reason=rationale,
            status="PENDING",
        )
        await req.insert()
        return {
            "exception_id": req.id,
            "finding_id": finding.id,
            "status": req.status,
            "reason": req.reason,
            "message": "Exception request submitted for human reviewer approval.",
        }

    async def _get_review_status(self, workspace_id: str, submission_id: str) -> Dict[str, Any]:
        """Checks publication readiness and certificate details."""
        sub = await Submission.get(submission_id)
        if not sub or sub.workspace_id != workspace_id:
            raise ValueError(f"Submission '{submission_id}' not found.")

        cert = await ComplianceCertificate.find_one(
            ComplianceCertificate.submission_id == submission_id
        )

        return {
            "submission_id": sub.id,
            "title": sub.title,
            "status": sub.status,
            "is_approved": sub.status == "APPROVED",
            "certificate_number": cert.certificate_number if cert else None,
            "certificate_hash": cert.certificate_hash if cert else None,
        }


mcp_service = MCPService()
