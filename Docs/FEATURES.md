# Feature Catalogue
## VeriBrand Trace

Status labels: `PLANNED` = in Round 1 concept; `SPECIFIED` = detailed in this documentation; `IMPLEMENTED` = only use after verified in code.

| Feature | Description | Primary role | Priority | Status |
|---|---|---|---|---|
| Brand workspace | Tenant/workspace for one brand with scoped RBAC | Admin | P0 | IMPLEMENTED |
| Brand Vault | Guidelines, facts, terminology and visual standards | Admin | P0 | PLANNED |
| Guideline ingestion | Import PDF/Markdown and preserve source references | Admin | P0 | PLANNED |
| Fact Registry | Approved facts and versioned claim evidence | Admin | P0 | PLANNED |
| Terminology rules | Banned, preferred and replacement terms | Admin | P0 | PLANNED |
| Visual rules | Approved hex values, logo and contrast rules | Admin | P0 | PLANNED |
| Content upload | Text, DOCX, PDF, PNG and JPG | Creator | P0 | PLANNED |
| Privacy scrubber | Mask configured PII and confidential terms | System | P0 | PLANNED |
| Deterministic audit | Terminology, numeric facts, colour and contrast | System | P0 | PLANNED |
| Grounded RAG audit | Tone, messaging and claim drift against approved facts | System | P0 | PLANNED |
| Violation cards | Rule/fact citations and evidence | Creator | P0 | PLANNED |
| Side-by-side diff | Intent-preserving suggestions and edits | Creator | P0 | PLANNED |
| Exception request | Justification for intentional deviations | Creator | P0 | PLANNED |
| Review queue | Pending audits and exceptions | Reviewer | P0 | PLANNED |
| Comments and sign-off | Review comments and approval/rejection | Reviewer | P0 | PLANNED |
| Compliance certificate | Evidence of approval and audit version | Reviewer | P1 | PLANNED |
| Governance insights | Recurring errors and ambiguous rules | Admin | P1 | PLANNED |
| Batch/multi-page processing | Higher-volume processing | System | P2 | Later-stage |

## Feature acceptance rule
Do not change a feature's status to `IMPLEMENTED` based on this plan alone. Verify the UI, API, persistence, permissions and tests first.
