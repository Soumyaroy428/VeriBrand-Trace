# Model Context Protocol (MCP) Design
## VeriBrand Trace

## 1. Status and scope
**Status:** IMPLEMENTED (Checkpoint 14).
Provides an authenticated, workspace-isolated Model Context Protocol (MCP) gateway (`/api/v1/mcp/tools/list` and `/api/v1/workspaces/{workspace_id}/mcp/tools/call`) allowing external LLMs, AI agents, and IDE tools (Cursor, Claude Desktop, Antigravity, VS Code) to query brand standards and execute compliance audits programmatically.

## 2. Design objective
Allow an authorised MCP client to invoke narrowly scoped brand-governance tools without bypassing the platform's authentication, workspace isolation, approval workflow or privacy gate.

## 3. Proposed tools
| Tool | Purpose | Permission |
|---|---|---|
| `get_brand_rules` | Retrieve active rules for a workspace | Member |
| `search_approved_facts` | Search approved fact registry | Member |
| `audit_text` | Submit text for a brand audit | Creator |
| `get_audit_findings` | Retrieve findings for an accessible audit | Resource owner/reviewer |
| `request_exception` | Submit exception rationale | Creator |
| `get_review_status` | Read review status | Resource owner/reviewer |

Do not expose unrestricted SQL, arbitrary file access, direct role mutation, direct approval, or publication tools.

## 4. Security requirements
- Authenticate MCP clients and bind identity to platform users.
- Derive workspace scope from verified identity/authorization context.
- Reuse the same service-layer permission checks as REST APIs.
- Validate all tool arguments with strict schemas.
- Apply rate limits, timeouts and audit logging.
- Return only data the caller may access.
- Treat tool output and retrieved content as untrusted.
- Require explicit user confirmation for sensitive or consequential actions.
- Do not allow an LLM to approve a submission or override a reviewer.

## 5. Resources and prompts
Potential read-only resources: active brand rule summaries, approved fact summaries and audit status. Avoid exposing raw confidential documents by default. Prompt templates should be versioned and must not contain secrets.

## 6. Deployment
If implemented, run the MCP server as a separate authenticated service or adapter. Do not expose an unauthenticated local-development MCP endpoint to the public internet. Use a documented transport supported by the chosen MCP SDK and client.

## 7. Acceptance criteria
- MCP calls enforce the same RBAC and tenant isolation as REST.
- Invalid arguments are rejected.
- Every call has a traceable audit event.
- No MCP tool can perform final approval or publishing.
- Tests cover malicious arguments, prompt injection, replay and cross-tenant access.
