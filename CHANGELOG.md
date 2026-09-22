# Changelog

All notable FSC release changes are documented here.

## [1.0.0-rc.2] - 2026-09-22

### Fixed
- Disabled the backend image's HTTP readiness healthcheck for non-HTTP worker containers.
- Full Stack E2E now starts the complete production Compose stack with `--wait`, so inherited worker healthcheck regressions fail CI.
- Added an explicit assertion that every worker overrides the backend HTTP healthcheck with Docker's disabled healthcheck.

### Deployment note
- `1.0.0-rc.1` remains published for traceability but should not be promoted further.
- `1.0.0-rc.2` supersedes rc.1 after the production acceptance run exposed the inherited worker healthcheck defect.

## [1.0.0-rc.1] - 2026-09-22

### Added
- PostgreSQL-backed ingestion, normalization, search, entity/topic detection and story clustering.
- Claim extraction, perspective attribution, cross-source claim grouping and contradiction relations.
- Evidence analysis, consensus/difference summaries, coverage gaps and missing-perspective analysis.
- Generation-consistent integrated Story Analysis API.
- Next.js Search, Story and Analysis frontend.
- Request correlation, structured HTTP observability, readiness/liveness checks and defensive security headers.
- Non-root production containers, health-gated Docker Compose startup and Nginx entry point.
- Full-stack E2E coverage including Alembic migrations and PostgreSQL backup/restore drill.
- Reproducible Python and Node dependency locks and warning-clean backend CI.

### Changed
- Backend CI treats Python warnings as errors.
- Production operations are documented with explicit backup, restore, upgrade and rollback procedures.
- Source administration is disabled by default unless explicitly configured.

### Known limitations
- Baseline analysis providers are intentionally conservative local rules and are not truth, credibility, bias or ideology scorers.
- Public TLS termination, production secrets, external monitoring and encrypted off-host backups are deployment-environment responsibilities.
