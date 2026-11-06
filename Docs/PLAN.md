# Development Plan
## VeriBrand Trace

## 1. Delivery approach
Build a thin end-to-end vertical slice first, then expand coverage. The phases below translate the Round 1 workflow into an actionable implementation sequence; dates and estimates are intentionally not assumed.

## 2. Phases and checkpoints
### Phase 0 — Project foundation
- Confirm repository layout and owners.
- Select vector store (ChromaDB or pgvector).
- Confirm storage, queue/background processing and deployment choices.
- Define environment variable names and secret handling.
**Exit:** architecture decisions recorded; application starts locally.

### Phase 1 — Identity and workspace
- Implement login/session lifecycle.
- Implement workspace membership and RBAC.
- Add workspace-scoped API authorization.
**Exit:** Creator, Reviewer and Governance Admin permissions are tested.

### Phase 2 — Brand Vault
- Import guidelines and parse source metadata.
- CRUD approved facts, terminology and visual rules.
- Add versioning and indexing pipeline.
**Exit:** a workspace can retrieve its own active rules/facts with source locations.

### Phase 3 — Submission and privacy
- Implement upload validation and private storage.
- Parse text, DOCX, PDF, PNG and JPG.
- Implement configurable PII/confidential-term redaction.
**Exit:** original file is preserved; redacted processing input is traceable.

### Phase 4 — Deterministic audit
- Terminology scanner.
- Approved fact/numeric comparison.
- Image colour extraction and Delta-E policy.
- WCAG contrast checks.
**Exit:** deterministic findings are reproducible and have evidence.

### Phase 5 — Grounded AI and RAG
- Chunk and embed Brand Vault content.
- Retrieve relevant evidence per audit.
- Integrate Gemini through a server-side adapter.
- Validate structured outputs with Pydantic.
**Exit:** AI findings cite retrieved sources or clearly report insufficient evidence.

### Phase 6 — Diff and exception workspace
- Violation cards and readiness summary.
- Side-by-side diff editor.
- Accept suggestion, manual edit and exception request.
**Exit:** original revision is immutable; edits create new revisions.

### Phase 7 — Review and governance
- Reviewer queue, comments, revision history and approval.
- Compliance certificate metadata/generation.
- Governance analytics.
**Exit:** complete approval trail and role-protected insights.

### Phase 8 — Hardening and release
- Security, accessibility, performance and failure testing.
- Monitoring, backups, retention and incident procedures.
- Deployment and rollback rehearsal.
**Exit:** release checklist signed by owners.

## 3. Suggested ownership from the PDF
| Member | Source-plan ownership |
|---|---|
| Sayantan Dutta | Backend architecture, RBAC workflow and telemetry |
| Soumya Roy | AIML lead, RAG pipeline and claim verification |
| Debarun Banerjee | Deterministic engine, computer vision and accessibility |
| Risijit Dhar | Frontend workspace and interactive diff UX |

## 4. Definition of done
- Requirements and acceptance criteria are met.
- Code review completed.
- Automated tests pass.
- No cross-workspace data leakage.
- Error and partial-failure states are visible.
- Documentation and environment examples are updated.
- No secrets or sensitive user content are committed to source control.

## 5. Risks and mitigations
| Risk | Mitigation |
|---|---|
| AI hallucination | Retrieval citations, schema validation and human review |
| PII leakage | Redaction gate, minimal context and provider controls |
| Incorrect deterministic rule | Unit tests, rule versioning and measured evidence |
| Cross-tenant leakage | Workspace filters, RLS and authorization tests |
| OCR errors | Confidence thresholds and manual review |
| Provider outage | Partial audit status, timeout and controlled retry |
