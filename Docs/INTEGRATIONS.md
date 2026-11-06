# External Integrations
## VeriBrand Trace

## 1. Integrations specified in the Round 1 plan
| Integration | Purpose | Data boundary |
|---|---|---|
| Gemini 2.5 Flash API | Grounded tone, messaging and claim-drift analysis | Redacted content plus retrieved evidence only |
| ChromaDB or pgvector | Retrieve relevant Brand Vault chunks | Workspace-scoped rule/fact chunks |
| Supabase PostgreSQL | Relational persistence and RBAC data | Application data and audit history |

## 2. Supporting infrastructure (proposed)
- Private object storage for original uploads and generated certificates.
- Email provider for optional reviewer notifications.
- Background worker/queue for OCR, parsing and long-running audits.
- Observability provider for metrics and error reporting.

These are proposed options, not vendors committed to by the PDF.

## 3. Gemini integration
- Keep API key server-side.
- Send only the minimum redacted content and relevant retrieved passages.
- Use a versioned prompt and strict JSON/Pydantic response schema.
- Set timeouts, token limits and controlled retries.
- Record model identifier, prompt version and request correlation ID.
- Handle quota/rate-limit/provider errors as incomplete AI analysis.
- Never treat an unsupported model statement as an approved fact.

## 4. Vector retrieval
Choose either ChromaDB or pgvector for the initial implementation. Store metadata such as workspace ID, source document ID, source version, page/section and chunk ID. Every retrieval query must filter by authorised workspace. Re-indexing a new source version must not silently erase the history needed to explain an old audit.

## 5. File and OCR pipeline
- Allow only configured file types and size limits.
- Validate actual file signatures, not just extensions.
- Store originals privately.
- Parse in a restricted worker with resource limits.
- Use OCR confidence and page/region metadata.
- Scan uploads for malware where suitable tooling is available.
- Delete temporary processing files according to retention policy.

## 6. Secrets and configuration
Use environment variables locally and a managed secret store in deployed environments. Rotate credentials, separate development/staging/production credentials and never commit `.env` files.

## 7. Integration failure policy
An unavailable external service must never create a false compliant result. Show partial audit status and identify the unavailable integration. Retry only safe/idempotent operations.
