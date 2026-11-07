# Feature Catalogue
## VeriBrand Trace

Status labels: `PLANNED` = in Round 1 concept; `SPECIFIED` = detailed in this documentation; `IMPLEMENTED` = only use after verified in code.

| Feature | Description | Primary role | Priority | Status |
|---|---|---|---|---|
| Brand workspace | Tenant/workspace for one brand with scoped RBAC | Admin | P0 | IMPLEMENTED |
| Brand Vault | Guidelines, facts, terminology and visual standards | Admin | P0 | IMPLEMENTED |
| Guideline ingestion | Import PDF/Markdown and preserve source references | Admin | P0 | IMPLEMENTED |
| Fact Registry | Approved facts and versioned claim evidence | Admin | P0 | IMPLEMENTED |
| Terminology rules | Banned, preferred and replacement terms | Admin | P0 | IMPLEMENTED |
| Visual rules | Approved hex values, logo and contrast rules | Admin | P0 | IMPLEMENTED |
| Content upload | Text, DOCX, PDF, PNG and JPG | Creator | P0 | IMPLEMENTED |
| Privacy scrubber | Mask configured PII and confidential terms | System | P0 | IMPLEMENTED |
| Deterministic audit | Terminology, numeric facts, colour and contrast | System | P0 | IMPLEMENTED |
| Grounded RAG audit | Tone, messaging and claim drift against approved facts | System | P0 | IMPLEMENTED |
| Violation cards | Rule/fact citations and evidence | Creator | P0 | IMPLEMENTED |
| Side-by-side diff | Intent-preserving suggestions and edits | Creator | P0 | IMPLEMENTED |
| Exception request | Justification for intentional deviations | Creator | P0 | IMPLEMENTED |
| Review queue | Pending audits and exceptions | Reviewer | P0 | IMPLEMENTED |
| Comments and sign-off | Review comments and approval/rejection | Reviewer | P0 | IMPLEMENTED |
| Compliance certificate | Evidence of approval and audit version | Reviewer | P1 | IMPLEMENTED |
| Governance insights | Recurring errors and ambiguous rules | Admin | P1 | IMPLEMENTED |
| Batch/multi-page processing | Higher-volume multi-item campaign processing | System | P2 | IMPLEMENTED |

## Feature acceptance rule
Do not change a feature's status to `IMPLEMENTED` based on this plan alone. Verify the UI, API, persistence, permissions and tests first.
