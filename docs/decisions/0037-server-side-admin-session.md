# ADR 0037: Server-side admin session

Status: Accepted
Date: 2026-10-01

## Context

FSC now has an administrative ArticleProvenance review queue and review-state
endpoint. The public Next.js frontend must not expose SOURCE_ADMIN_API_KEY to a
browser, and a full user/role or external identity platform is not yet justified
for the current single-operator deployment.

## Decision

Administrative UI routes use a small server-side authentication boundary in
Next.js.

- FSC_ADMIN_PASSWORD is a deployment secret used only by the Next.js server.
- FSC_ADMIN_SESSION_SECRET signs an opaque session token stored in an HttpOnly,
  Secure (in production), SameSite=Strict cookie.
- The token contains only an expiry and random nonce; it contains no backend
  credential or user data.
- Administrative Server Actions verify the session before every privileged
  operation.
- Next.js calls FastAPI from the server and adds SOURCE_ADMIN_API_KEY there.
  The backend keeps its existing independent admin-key protection.
- The initial admin surface is limited to ArticleProvenance review.
- No registration, password reset, user table, roles, or browser-visible API key
  are introduced.
- The boundary may later replace password verification with OIDC without
  changing the provenance review API.

## Consequences

The browser never receives SOURCE_ADMIN_API_KEY or either admin deployment
secret. Compromise of a browser session does not reveal the backend credential.
The deployment gains two new required frontend secrets before the admin UI can
be enabled.

The session is deliberately single-operator and authorization is binary. A
future requirement for named reviewers, per-user audit attribution, MFA, or
roles requires a follow-up identity decision rather than extending this token
with ad-hoc identity semantics.
