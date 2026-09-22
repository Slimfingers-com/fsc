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
