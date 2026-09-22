# FSC 1.0.0-rc.2 Release Candidate

This release candidate supersedes `1.0.0-rc.1`.

## Why rc.2 exists

The first production acceptance deployment showed that worker containers inherited the backend image's HTTP readiness healthcheck. The workers themselves were processing successfully, but Docker marked them unhealthy because they intentionally do not run an HTTP server on port 8000.

## Fixed

- All worker services explicitly disable the inherited backend HTTP healthcheck.
- Full Stack E2E starts the complete production Compose stack with `docker compose up -d --wait`.
- CI verifies every worker has Docker healthchecking disabled instead of inheriting the backend HTTP probe.

## Included baseline

rc.2 otherwise contains the same feature-complete FSC baseline as rc.1: ingestion, normalized search, entity/topic and story analysis, claims, perspectives, cross-source relations, evidence, consensus/differences, coverage gaps, integrated analysis API, Next.js frontend, observability, secure-by-default Compose networking, backup/restore tooling, dependency locks and automated release promotion.

## Promotion prerequisites

Complete the production-environment checklist in GitHub issue #22 and follow `docs/operations/production.md`.
