# FSC Production Operations

This runbook describes the baseline single-host Docker Compose deployment for FSC.

## Network boundary and TLS

The bundled Nginx service binds to `127.0.0.1:${FSC_HTTP_PORT:-8080}` only. Do not expose that plain-HTTP listener directly to the public internet.

Terminate HTTPS in a host-level reverse proxy, load balancer, or equivalent trusted edge and proxy to the loopback FSC listener. Only the TLS entry point should be reachable from untrusted networks.

The Next.js and FastAPI ports are also bound to loopback. PostgreSQL and Redis are not published to the host.

## Environment and secrets

Create the production environment from `.env.example` and restrict access:

```sh
cp .env.example .env
chmod 600 .env
```

Replace at least:

- `DATABASE_PASSWORD` with a unique random password.
- `SECRET_KEY` with a unique random value.
- `SOURCE_ADMIN_API_KEY` only if source administration is required.

An empty `SOURCE_ADMIN_API_KEY` disables source administration and is the recommended default until the endpoint is needed.

Example secret generation:

```sh
openssl rand -hex 32
```

Never commit `.env` or backup archives.

## Initial deployment

From the repository root:

```sh
COMPOSE="docker compose --env-file .env -f infrastructure/docker/docker-compose.yml"

$COMPOSE build
$COMPOSE up -d --wait postgres
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE up -d
```

Check readiness:

```sh
curl --fail http://127.0.0.1:8000/health/ready
curl --fail http://127.0.0.1:${FSC_HTTP_PORT:-8080}/
```

FastAPI readiness returns 503 when PostgreSQL is unavailable or the database schema is not at the current Alembic head.

## Backup

Create a validated custom-format PostgreSQL dump:

```sh
bash infrastructure/backup/backup.sh
```

By default backups are written to `./backups` with mode 0600 plus a SHA-256 checksum. Override the location with `FSC_BACKUP_DIR`:

```sh
FSC_BACKUP_DIR=/srv/fsc-backups \
  bash infrastructure/backup/backup.sh
```

Backups stored only on the application host are not sufficient. Copy them to encrypted off-host storage and apply an external retention policy appropriate for the deployment.

Run backups on a schedule and periodically verify that recent archives and checksum files exist.

## Restore

A restore is intentionally destructive and requires explicit confirmation:

```sh
FSC_RESTORE_CONFIRM=RESTORE \
  bash infrastructure/backup/restore.sh \
  /srv/fsc-backups/fsc-YYYYmmddTHHMMSSZ.dump
```

The restore procedure:

1. verifies the SHA-256 checksum when present;
2. stops FSC services without deleting Docker volumes;
3. starts PostgreSQL only;
4. validates and restores the custom-format dump;
5. applies any newer Alembic migrations;
6. leaves application services stopped for inspection.

After verification, start FSC again:

```sh
COMPOSE="docker compose --env-file .env -f infrastructure/docker/docker-compose.yml"

$COMPOSE up -d
```

Worker services intentionally do not expose HTTP health endpoints. Their inherited backend image healthcheck is disabled in Compose. Use the readiness checks below to verify the healthchecked web path after startup rather than applying `docker compose --wait` to the complete mixed worker/web stack.

The Full Stack E2E workflow executes a real backup/restore drill on every relevant change.

## Upgrade

Before an application or dependency upgrade:

```sh
bash infrastructure/backup/backup.sh
```

Then update and migrate in this order:

```sh
COMPOSE="docker compose --env-file .env -f infrastructure/docker/docker-compose.yml"

$COMPOSE build
$COMPOSE up -d --wait postgres
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE up -d
```

Do not rely on application startup to migrate the database.

## Rollback

Application rollback and database rollback are separate concerns. Do not run automatic Alembic downgrades against production data.

If a previous application version is compatible with the migrated schema, redeploy that image/version. If the migration itself must be reverted, restore a verified pre-upgrade backup instead.

## Monitoring and logs

Use:

```sh
docker compose --env-file .env \
  -f infrastructure/docker/docker-compose.yml ps

docker compose --env-file .env \
  -f infrastructure/docker/docker-compose.yml logs --tail=200
```

Container JSON logs are capped at 10 MB per file with five files retained per service. Central log shipping and external uptime monitoring are deployment concerns and should use `X-Request-ID` to correlate frontend/backend failures.

Monitor at minimum:

- HTTPS availability at the external edge;
- FastAPI `/health/ready`;
- PostgreSQL disk usage;
- backup freshness and off-host copy success;
- container restart loops;
- ingestion/analysis worker error rates.

### Production quality report

`scripts/production-quality-report.sh` appends a compact production-quality
snapshot to `/home/sven/fsc-monitor/quality.log` by default. It measures
pipeline completion, Story/source coverage and integrated-analysis output.
`article_states_with_error` and `story_states_with_error` count only unresolved
current errors: a historical error no longer counts after a newer successful
processing timestamp.

A daily production schedule can invoke the versioned script directly, for
example:

```cron
5 3 * * * /bin/bash /home/sven/fsc/scripts/production-quality-report.sh
```

The runner uses an overlap lock and keeps the SQL definition versioned in
`scripts/production-quality-report.sql`.

## Release checklist

Before promoting a release candidate:

- Backend Tests are green.
- Frontend Tests are green.
- Full Stack E2E is green.
- Dependency locks are current.
- Alembic upgrades from an empty database succeed.
- A backup/restore drill succeeds.
- Production images run as non-root.
- `.env` contains no placeholder secrets.
- TLS termination and firewall rules are active.
- A recent encrypted off-host database backup exists.


## Controlled FSC release publication (manual approval)

**Policy A:** Passing CI, a successful production deployment, or closing a
GitHub issue must **never** publish a GitHub Release automatically. In
particular, do not enable the old `workflow_run` publication proposal in PR
#24. Publishing is a separate, deliberate operator action.

### Prepare and verify the exact release commit

1. Complete the v1.0 product-quality acceptance in issue
   [#29](https://github.com/Slimfingers-com/fsc/issues/29). Keep that issue
   open until its full production-cycle and manual quality requirements are
   actually met. Release publication is blocked while it is open.
2. In a reviewed PR, update `VERSION`, `CHANGELOG.md`, the frontend package
   and lock versions, and `docs/operations/release-<version>.md`. Do not
   create the version tag or GitHub Release in the PR.
3. Merge the reviewed release metadata to `main`. The Backend Tests,
   Frontend Tests, Full Stack E2E and Release Metadata workflows run
   automatically on the resulting main commit. Record its full 40-character
   SHA. If any check is missing, failing, or not finished, do not publish.
   Each workflow also supports manual reruns on main for operational recovery.
4. The Release Metadata workflow automatically verifies metadata consistency
   and the fail-closed release gate regression tests. No release is produced.

### Manually publish after approval

1. On GitHub, open **Actions → Publish FSC Release (Manual Approval) →
   Run workflow** and select **main**.
2. Enter the exact version (such as `1.0.0`), the full reviewed `main`
   commit SHA, and the confirmation phrase
   `PUBLISH FSC <version>` (for example `PUBLISH FSC 1.0.0`).
3. The workflow fails closed unless the selected commit is still `main`
   HEAD, version metadata and release notes agree, issue #29 is **closed**,
   no tag already exists, and **all four** required CI workflows succeeded
   on that **exact commit**. Green checks on earlier commits or PR-only
   runs are not acceptable.
4. The publish job uses the `release-publication` GitHub Environment.
   **Repository maintainers should configure required reviewers** in
   Settings → Environments → release-publication for an additional
   human approval after preflight. The workflow does not configure
   those reviewer settings and cannot assume they are enabled.
5. After any environment approval, the workflow rechecks the exact commit,
   product-acceptance issue, metadata, existing tag and CI gates before
   creating the release. It verifies the resulting tag points to the
   approved SHA. Prerelease versions are published as prereleases.

Only the explicit **Run workflow** action with the version-specific
confirmation phrase can start publication. Normal commits, tags, CI
successes, deploys, and the production-quality monitor never publish.
This workflow creates a GitHub Release; it does **not** deploy to Hetzner.

Existing `v1.0.0-rc.1` and `v1.0.0-rc.2` tags/releases remain untouched.
Do not reuse an existing tag or bump the production VERSION silently.
