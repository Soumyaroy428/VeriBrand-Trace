# Product & UX Design Specification
## VeriBrand Trace

## 1. Design principles
- Explain before suggesting.
- Preserve the creator's original voice.
- Never silently alter or publish content.
- Make source evidence visible beside every finding.
- Separate deterministic facts from probabilistic AI observations.
- Keep reviewer decisions auditable.

## 2. Information architecture
1. Authentication: sign in, sign out, password recovery.
2. Workspace selector: available brand workspaces.
3. Creator workspace: new audit, upload history, audit detail and diff editor.
4. Brand Vault: guidelines, approved facts, terminology, visual rules and assets.
5. Review queue: pending reviews, exception requests and revision history.
6. Governance dashboard: recurring violations, override rates and rule trends.
7. Administration: users, roles, workspace settings and integrations.

## 3. Core screens
### Dashboard
Show recent audits, status counts, pending reviews and shortcuts. Scope every metric to the active workspace and the viewer's permissions.

### New audit
Provide supported file types, upload progress, privacy notice and explicit confirmation before processing. Display file validation errors before starting analysis.

### Audit results
Show readiness summary, severity filters, deterministic/AI source labels and violation cards. Each card contains:
- Finding title and severity.
- Exact guideline clause or approved fact reference.
- Evidence and measured values where applicable.
- Engine/source label.
- Suggested change, if available.
- Actions: Accept suggestion, Edit manually, Request exception.

### Diff workspace
Use a side-by-side original/proposed view. Highlight additions and removals. Applying a suggestion creates a new revision; it must not overwrite the original revision.

### Reviewer workspace
Show unresolved issues, comments, exception rationale, revision diffs and approval controls. Require an explicit decision and optionally a reviewer note.

### Brand Vault
Use separate sections for guideline documents, approved facts, terminology, visual standards and assets. Show source, version, effective date, owner and status.

### Governance insights
Display counts and trends with filters by time, team and rule category. Avoid exposing individual creator content to users without permission.

## 4. Design system
- Frontend from source plan: Next.js 14, TypeScript, Tailwind CSS and TipTap.
- Use semantic HTML, keyboard-accessible controls and visible focus states.
- Use consistent status labels: Draft, Processing, Needs changes, Pending review, Approved, Rejected, Failed.
- Use severity labels: Critical, High, Medium, Low, Informational. Final mapping is an implementation decision.
- Do not use colour alone to communicate status.
- Provide empty, loading, success, partial-failure and error states.

## 5. Interaction rules
- Uploads show accepted formats and validation limits.
- Long-running audits show progress by processing stage.
- AI suggestions require explicit user acceptance.
- Exceptions require a reason and are visibly marked as exceptions, not as passed checks.
- Approval is disabled while required blocking findings remain unresolved, subject to workspace policy.
- Every state-changing action provides confirmation and a resulting audit event.

## 6. Accessibility
Target WCAG 2.1 AA for the application. Ensure keyboard operation, accessible labels, sufficient UI contrast, screen-reader announcements for asynchronous status changes and non-colour indicators for diff changes.

## 7. Responsive behaviour
Support desktop-first side-by-side editing. On narrow screens, stack original and proposed content vertically and keep actions accessible without horizontal page scrolling.
