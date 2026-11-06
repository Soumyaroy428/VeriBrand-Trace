# Product Requirements Document (PRD)
## VeriBrand Trace
**Team:** Last of Us  
**Submission basis:** Round 1 plan (5-page PDF)  
**Status:** Draft implementation specification

## 1. Product overview
VeriBrand Trace is an explainable, human-in-the-loop brand governance platform that audits content before publication. It combines deterministic checks with citation-grounded AI analysis and gives creators traceable findings and intent-preserving suggestions. It does not publish or silently rewrite content.

## 2. Problem
The Round 1 plan identifies four recurring problems:
- Unsupported or outdated claims, including unverified superlatives and stale figures.
- Inconsistent terminology and brand tone.
- Visual non-compliance, including unauthorized colours, logo rules and accessibility contrast.
- Opaque review processes that block work or rewrite content without explaining why.

The plan reports a 14-person practitioner study: 78.6% rarely/never consult static brand PDFs after onboarding; 85.7% cited repetitive mechanical errors; 64.3% reported vague rejections or invasive rewrites; 71.4% skip banner contrast checks. These are team-reported findings; retain the original survey method and sample size whenever quoting them.

## 3. Goals
1. Provide pre-publication checks for text, DOCX/PDF documents and PNG/JPG images.
2. Explain each finding with the exact guideline clause, approved fact ID or visual rule.
3. Separate deterministic results from AI-assisted judgements.
4. Offer non-destructive, per-issue suggestions and side-by-side diffs.
5. Support justified exceptions and human reviewer approval.
6. Maintain revision history and tamper-evident approval evidence.
7. Give administrators insight into recurring mistakes and ambiguous rules.

## 4. Non-goals
- Autonomous publishing or automatic final approval.
- Replacing legal, compliance or human brand review.
- Treating AI output as authoritative evidence without source citations.
- Scraping private bank, social or other unrelated account data.
- Guaranteeing that every possible brand or legal issue can be detected.

## 5. Users and permissions
### Creator
Uploads content, reviews findings, accepts or edits suggestions, and requests exceptions with justification.

### Authorised Reviewer
Reviews unresolved violations, claim evidence, revision history and exceptions; comments and approves or rejects publication readiness.

### Governance Admin
Manages Brand Vault content, facts, terminology, visual rules, users/roles and governance analytics.

A platform operator role may be added for deployment operations, but it must not silently inherit brand approval authority.

## 6. Primary workflow
1. Admin creates a brand workspace and imports guidelines, approved facts, terminology and visual standards.
2. Creator submits text, DOCX/PDF or PNG/JPG content.
3. Privacy gate detects and masks configured PII and confidential project terms before external AI processing.
4. Deterministic engine checks terminology, exact facts, colours and WCAG contrast.
5. RAG-based AI evaluates tone, messaging and claim drift using retrieved Brand Vault evidence.
6. Workspace presents a readiness score and traceable violation cards.
7. Creator accepts a suggestion, edits manually or requests an exception.
8. Reviewer inspects changes, comments and exceptions, then approves or rejects.
9. Approval produces a compliance certificate and immutable audit event.
10. Admin reviews aggregate patterns and ambiguous rules.

## 7. Functional requirements
| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Authenticate users and enforce workspace-scoped RBAC | P0 |
| FR-02 | Create and manage brand workspaces | P0 |
| FR-03 | Upload and version guidelines, fact sheets and visual assets | P0 |
| FR-04 | Parse text, DOCX, PDF, PNG and JPG submissions | P0 |
| FR-05 | Apply privacy redaction before external AI calls | P0 |
| FR-06 | Run deterministic terminology, fact, colour and contrast checks | P0 |
| FR-07 | Run grounded RAG analysis with source references | P0 |
| FR-08 | Display traceable violation cards and side-by-side diffs | P0 |
| FR-09 | Support accept, manual edit and exception request actions | P0 |
| FR-10 | Support reviewer comments and approval/rejection | P0 |
| FR-11 | Store revision history and audit events | P0 |
| FR-12 | Generate a compliance certificate after approval | P1 |
| FR-13 | Provide governance analytics | P1 |
| FR-14 | Support batch/multi-page processing | P2; later-stage capability |

## 8. Non-functional requirements
- Security: workspace isolation, least privilege, secure secrets and upload validation.
- Explainability: every finding must identify its rule/fact source or be labelled as an AI observation without verified evidence.
- Reliability: deterministic checks must be reproducible for the same input and rule version.
- Privacy: redact configured sensitive content before sending data to external providers.
- Accessibility: target WCAG 2.1 AA for the application UI and evaluate submitted creative assets against configured contrast rules.
- Performance: establish measurable targets after baseline profiling; do not promise unmeasured latency.
- Observability: structured logs, correlation IDs and audit events without logging raw sensitive content.

## 9. Readiness score
The PDF proposes a Brand Readiness Score but does not define its formula. Initial implementation should show counts by severity and a transparent score formula configured and versioned by admins. Do not present the score as a legal compliance guarantee.

## 10. Acceptance criteria
- A creator can submit a supported file and receive a completed audit or actionable processing error.
- Each deterministic finding identifies the rule and measured evidence.
- Each AI finding includes retrieved source references or is marked ungrounded/needs review.
- The creator's original content remains unchanged until the creator explicitly applies a diff.
- A creator cannot approve their own submission unless an explicitly configured policy allows it.
- Review decisions and exception decisions are recorded with actor, timestamp and revision.
- Only authorised admins can alter Brand Vault rules and facts.
- External AI requests receive redacted content according to workspace privacy settings.

## 11. Open decisions
- ChromaDB or pgvector: select one primary vector store for the first release.
- Supabase hosting and storage configuration.
- Exact PII detection policy and supported redaction categories.
- Supported maximum upload size and page count.
- Readiness score formula and severity weights.
- Certificate signing/verification method.
- Whether MCP tools are enabled in the first release.
