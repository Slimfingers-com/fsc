# ADR 0038: ZITADEL OIDC for admin identity

Status: Accepted
Date: 2026-10-02

## Context

ADR 0037 introduced a single-operator password boundary for the first provenance
review UI. FSC should support named reviewers and stronger authentication without
becoming a password or MFA provider itself.

## Decision

FSC delegates interactive admin authentication to ZITADEL Cloud using OpenID
Connect Authorization Code with PKCE. The ZITADEL instance uses the EU data
region.

- NextAuth handles the OIDC browser flow and the FSC server-side session.
- The browser never receives SOURCE_ADMIN_API_KEY.
- FastAPI keeps X-FSC-Admin-Key as an independent server-to-server boundary.
- Initial authorization is fail-closed to FSC_ADMIN_EMAIL.
- ZITADEL issuer, client credentials and NextAuth secret are deployment secrets.
- The previous shared FSC_ADMIN_PASSWORD authentication is retired.
- Additional reviewers later require explicit authorization policy changes;
  successful ZITADEL authentication alone does not grant FSC admin access.

## Consequences

FSC no longer stores or verifies an administrator password and does not implement
password reset or MFA. Identity lifecycle and MFA can be provided by ZITADEL,
while FSC retains control over application authorization.

The OIDC integration remains standards-based so the identity provider can be
replaced without changing the provenance API or exposing its backend admin key.
