# Testing and Quality Assurance
## VeriBrand Trace

## 1. Testing objectives
Verify correctness, explainability, privacy, security, accessibility and resilience. Test deterministic and AI systems separately because their expected behaviour differs.

## 2. Test levels
### Unit tests
- Terminology matching, case sensitivity and word boundaries.
- Numeric fact comparison and tolerance rules.
- Colour extraction and Delta-E calculations.
- WCAG contrast calculations.
- PII redaction and confidential-term masking.
- Pydantic schemas and severity mapping.
- Permission decision functions.

### Integration tests
- API + PostgreSQL persistence.
- Brand Vault ingestion and retrieval.
- File parsing and OCR pipeline.
- Gemini adapter with mocked provider responses.
- Audit orchestration and partial-failure handling.
- Revision creation, exception and approval transitions.

### End-to-end tests
- Creator submits content and reviews findings.
- Creator applies a suggestion and creates a new revision.
- Creator requests an exception.
- Reviewer comments and approves/rejects.
- Admin updates a rule and verifies version history.
- Unauthorised user cannot access another workspace's data.

## 3. Deterministic engine test cases
| Area | Positive case | Negative/edge case |
|---|---|---|
| Terminology | Banned term is found | Similar substring should not false-match |
| Numeric fact | Exact approved value passes | Outdated or altered value is flagged |
| Colour | Approved hex is accepted | Out-of-policy colour is flagged |
| Contrast | Ratio meets configured threshold | Ratio below threshold is flagged |
| OCR | Clear text is extracted | Low-confidence OCR is marked uncertain |

Mathematical checks should be deterministic for fixed inputs, but extraction and OCR can be uncertain. Never describe the entire image pipeline as having zero error.

## 4. AI/RAG evaluation
Create a curated evaluation set with:
- Supported claims.
- Contradicted claims.
- Claims with no evidence.
- Tone mismatches.
- Conflicting or outdated guideline versions.
- Prompt-injection text inside uploaded documents.
Measure citation correctness, unsupported-claim detection, false positives/negatives and schema validity. Human reviewers should label evaluation examples.

## 5. Security and privacy tests
- Cross-workspace access attempts.
- Role escalation and IDOR.
- Malicious/oversized uploads.
- File parser resource exhaustion.
- Secret leakage in client bundles/logs.
- PII redaction before external API request.
- Prompt injection and tool abuse.
- Session expiry, refresh replay and CSRF where applicable.

## 6. Accessibility tests
- Keyboard-only operation.
- Screen-reader labels and announcements.
- Focus order and focus visibility.
- UI contrast and non-colour status indicators.
- Submitted image contrast checks against configured rules.

## 7. Release gates
- Critical tests pass.
- No known cross-tenant access vulnerability.
- No secret committed or exposed.
- Partial engine failures are visible.
- AI findings include evidence or explicit uncertainty.
- Manual approval remains required.
- Database migrations and rollback plan are reviewed.
