# FSC 1.0.0-rc.1 Release Candidate

This is the first feature-complete FSC Release Candidate.

## Included

FSC now covers the full baseline pipeline from ingestion to integrated debate analysis:

- feed ingestion and normalized article persistence;
- PostgreSQL search and discovery;
- entity/topic detection and story clustering;
- factual claim extraction and perspective attribution;
- cross-source claim groups and contradiction relations;
- traceable evidence classification;
- structural consensus and difference summaries;
- coverage gaps and missing-perspective indicators;
- generation-consistent integrated Story Analysis API;
- responsive Next.js frontend for Search, Stories and Analysis.

## Release hardening

The RC includes:

- dependency lockfiles for reproducible builds;
- non-root backend/frontend containers;
- database-schema-aware readiness;
- health-gated Compose startup;
- Nginx loopback entry point;
- request IDs, structured HTTP logs and security headers;
- backend CI with warnings treated as errors;
- full-stack E2E through Nginx -> Next.js -> FastAPI -> PostgreSQL;
- real PostgreSQL backup -> mutate -> restore -> verify testing.

## Important semantics

FSC presents observable source coverage, claims, evidence, attribution, consensus structure and explicit contradictions. It does not produce truth scores, source-credibility scores, political rankings or ideology labels.

## Promotion prerequisites

Before deploying this RC outside a test environment, complete the production-environment checklist in GitHub issue #22 and follow `docs/operations/production.md`.
