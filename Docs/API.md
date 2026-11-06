# API Specification
## VeriBrand Trace

**Backend:** FastAPI + Pydantic v2 (source plan).  
This is a proposed first-version REST contract; endpoint names and schemas must be aligned with the implemented code.

## 1. Conventions
- Prefix: `/api/v1`
- JSON request/response unless uploading multipart files.
- Authentication: `Authorization: Bearer <access-token>`.
- Use UUID identifiers.
- Return consistent errors: `{"error":{"code":"...","message":"...","request_id":"..."}}`.
- Validate workspace membership and role on every workspace-scoped endpoint.
- Use pagination (`limit`, `cursor`) for collections.
- Use idempotency keys for submission creation and approval actions where retries are possible.

## 2. Authentication
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/login` | Authenticate |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke refresh session |
| GET | `/auth/me` | Current user |

The actual identity provider and password/session implementation are deployment decisions.

## 3. Workspaces and Brand Vault
| Method | Endpoint | Role |
|---|---|---|
| GET | `/workspaces` | Member |
| POST | `/workspaces` | Admin/platform policy |
| GET | `/workspaces/{workspace_id}/members` | Admin |
| POST | `/workspaces/{workspace_id}/members` | Admin |
| POST | `/workspaces/{workspace_id}/guidelines` | Admin |
| GET | `/workspaces/{workspace_id}/guidelines` | Member |
| POST | `/workspaces/{workspace_id}/facts` | Admin |
| GET | `/workspaces/{workspace_id}/facts` | Member |
| POST | `/workspaces/{workspace_id}/terminology-rules` | Admin |
| POST | `/workspaces/{workspace_id}/visual-rules` | Admin |

## 4. Submissions and audits
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/workspaces/{workspace_id}/submissions` | Create submission/upload |
| GET | `/submissions/{submission_id}` | Submission detail |
| GET | `/submissions/{submission_id}/revisions` | Revision list |
| POST | `/submissions/{submission_id}/audits` | Start audit |
| GET | `/audits/{audit_id}` | Audit status and summary |
| GET | `/audits/{audit_id}/findings` | Findings with evidence |
| POST | `/submissions/{submission_id}/revisions` | Create edited revision |

## 5. Findings, exceptions and reviews
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/findings/{finding_id}/apply-suggestion` | Apply accepted suggestion as a new revision |
| POST | `/findings/{finding_id}/exceptions` | Request exception |
| GET | `/workspaces/{workspace_id}/review-queue` | Reviewer queue |
| POST | `/submissions/{submission_id}/comments` | Add reviewer comment |
| POST | `/exceptions/{exception_id}/decision` | Approve/reject exception |
| POST | `/submissions/{submission_id}/approval` | Approve/reject publication readiness |
| GET | `/submissions/{submission_id}/certificate` | Retrieve certificate metadata/document |

## 6. Example finding response
```json
{
  "id": "uuid",
  "category": "CLAIM_ACCURACY",
  "severity": "HIGH",
  "source_engine": "RAG_AI",
  "title": "Claim requires verification",
  "description": "The statement could not be supported by the approved fact registry.",
  "evidence": [
    {
      "source_type": "APPROVED_FACT",
      "source_id": "uuid",
      "source_version": 2,
      "quote": "Approved fact excerpt"
    }
  ],
  "suggestion": {
    "text": "Suggested alternative wording",
    "requires_user_acceptance": true
  },
  "status": "OPEN"
}
```

## 7. Example error codes
`UNAUTHENTICATED`, `FORBIDDEN`, `WORKSPACE_NOT_FOUND`, `FILE_TYPE_NOT_ALLOWED`, `FILE_TOO_LARGE`, `PARSING_FAILED`, `AUDIT_IN_PROGRESS`, `AI_PROVIDER_UNAVAILABLE`, `RETRIEVAL_UNAVAILABLE`, `VALIDATION_ERROR`, `CONFLICT`.

## 8. API security
- Enforce role and workspace checks server-side.
- Validate MIME type and file signature; do not trust filename extensions.
- Rate-limit login, upload and AI-triggering endpoints.
- Never return provider API keys or storage credentials.
- Avoid returning raw redacted/original content unless caller is authorised.
- Log request IDs and action metadata, not sensitive payloads.
