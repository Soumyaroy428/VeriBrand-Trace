# Debugging and Operations Guide
## VeriBrand Trace

## 1. General diagnostic sequence
1. Capture the request/correlation ID and audit run ID.
2. Identify the failing stage: upload, parsing, privacy, deterministic, retrieval, AI, persistence or review.
3. Inspect structured logs and stage status.
4. Check dependency health and configuration without printing secret values.
5. Reproduce with a sanitised test fixture.
6. Fix the root cause, add a regression test and document the resolution.

## 2. Common failure scenarios
| Symptom | Likely cause | Safe checks |
|---|---|---|
| Database connection fails | Incorrect URL, network or credentials | Confirm host/port/database and secret presence; do not print password |
| Migration fails | Schema drift or migration conflict | Inspect migration history and current schema |
| Upload rejected | Unsupported type/size or signature mismatch | Check configured allowlist and actual file signature |
| PDF/DOCX parsing fails | Corrupt, encrypted or unsupported document | Test a known-good fixture; report parsing failure clearly |
| OCR output is poor | Low resolution, low contrast or unsupported layout | Inspect confidence and source page; request a better source |
| Vector search returns no evidence | Index missing, stale or wrong workspace filter | Check indexing status, source version and tenant filter |
| Gemini request fails | Missing key, quota, timeout or provider outage | Verify server-side configuration and provider status |
| AI output schema invalid | Model returned malformed/unexpected structure | Preserve safe diagnostics; reject output and mark AI stage failed |
| Findings missing | Stage failed or normalizer dropped an item | Compare raw validated engine output with normalized records |
| User sees forbidden data | RBAC or workspace filter defect | Treat as security incident; disable affected access and investigate |
| Certificate unavailable | Approval incomplete or generation failed | Verify approval event and certificate job status |

## 3. Logging rules
Log:
- Timestamp, severity, service and correlation ID.
- Audit run ID and processing stage.
- Error code and safe diagnostic metadata.
- Provider/model identifier where relevant.

Do not log:
- Passwords, tokens, API keys or database credentials.
- Unredacted PII or confidential project terms.
- Full uploaded documents or raw prompts containing sensitive content.

## 4. Operational states
Use explicit states such as `QUEUED`, `PROCESSING`, `PARTIAL`, `COMPLETED`, `FAILED`, `CANCELLED`. A failed AI stage must not be represented as a successful full audit.

## 5. Incident response
For suspected cross-tenant exposure or secret leakage:
1. Restrict or disable the affected endpoint/integration.
2. Preserve relevant audit/security logs.
3. Rotate exposed credentials.
4. Determine scope and affected workspaces.
5. Notify responsible project/security owners.
6. Patch, test and review before restoring service.

## 6. Debugging checklist
- [ ] Is the correct environment loaded?
- [ ] Are required secrets present without exposing their values?
- [ ] Is PostgreSQL reachable?
- [ ] Are migrations current?
- [ ] Is the selected vector store reachable and indexed?
- [ ] Is the file valid and within limits?
- [ ] Did redaction run before external processing?
- [ ] Did deterministic and AI stages report independent statuses?
- [ ] Are source references and rule versions attached?
- [ ] Was every state-changing action audited?
