# Authentication and Authorization
## VeriBrand Trace

**Source-plan decision:** JWT Auth and RBAC with PostgreSQL/Supabase.  
**Implementation detail:** Proposed; identity provider and token lifecycle require confirmation.

## 1. Roles
| Permission | Creator | Authorised Reviewer | Governance Admin |
|---|---:|---:|---:|
| Submit content | Yes | Optional | Optional |
| View own submissions | Yes | Yes | Yes |
| View workspace submissions | Policy-limited | Yes | Yes |
| Apply suggestions to own revision | Yes | Optional | Optional |
| Request exception | Yes | No | No |
| Decide exception | No | Yes | Policy |
| Comment on review | No | Yes | Yes |
| Approve/reject publication readiness | No | Yes | Policy |
| Manage Brand Vault | No | No | Yes |
| Manage workspace members/roles | No | No | Yes |
| View governance analytics | No | Limited | Yes |

Default-deny applies. A user's role is scoped to a workspace, not globally inferred from a client-side claim.

## 2. Authentication lifecycle
- Use a vetted identity/password implementation or trusted identity provider.
- Verify credentials server-side.
- Issue short-lived access tokens and rotate refresh tokens if using refresh sessions.
- Store refresh tokens securely (hashed server-side; secure, HttpOnly, SameSite cookies where browser sessions are used).
- Revoke sessions on logout, password reset and suspected compromise.
- Implement rate limits and generic login errors to reduce account enumeration.
- Require strong secrets and TLS in production.

## 3. Authorization
- Resolve user identity from a verified token/session.
- Load membership for the requested workspace.
- Check permission for the action and resource.
- Apply workspace scoping to every database query and file access.
- Never trust `role`, `user_id` or `workspace_id` supplied by the browser without server-side verification.
- Use PostgreSQL RLS as defence in depth, not as a replacement for application checks.

## 4. Sensitive actions
Require explicit confirmation and audit events for:
- Role changes.
- Brand Vault rule/fact activation or deactivation.
- Exception decisions.
- Final approval/rejection.
- Certificate generation or revocation.

## 5. Account and session security
- Password reset tokens must be random, short-lived and single-use.
- Protect against CSRF when cookie-based authentication is used.
- Validate JWT issuer, audience, signature, expiry and algorithm.
- Do not store access tokens in localStorage by default when a secure cookie session is viable.
- Remove secrets from logs and error traces.

## 6. Audit events
Record actor, workspace, action, target, timestamp, request/correlation ID and safe metadata. Do not log passwords, bearer tokens, raw PII or full confidential content.

## 7. Security tests
Test unauthenticated access, role escalation, cross-workspace IDOR, expired/revoked tokens, refresh-token replay, CSRF where relevant and direct file URL access.
