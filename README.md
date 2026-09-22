# FSC – Fair Spectrum Compass

FSC ist eine Plattform zur transparenten Analyse öffentlicher Debatten.

Ziel ist es, Ereignisse nicht nur als Nachrichten darzustellen, sondern Perspektiven, Claims, Evidenz, Konsens, Unterschiede, Coverage Gaps und fehlende Perspektiven sichtbar zu machen.

## Search & Discovery

Normalisierte Artikel werden durch einen eigenen Worker in versionierte `SearchDocument`-Datensätze überführt. `GET /search` bietet PostgreSQL-Volltextsuche sowie Discovery ohne Suchtext.

Unterstützte Parameter: `q`, `language`, `source_id`, `source`, `published_from`, `published_to`, `sort` (`relevance`, `newest`, `oldest`), `page` und `page_size`. Die Seitengröße ist über `SEARCH_DEFAULT_PAGE_SIZE` und `SEARCH_MAX_PAGE_SIZE` konfigurierbar; der Reindex-Worker über `SEARCH_WORKER_POLL_INTERVAL_SECONDS` und `SEARCH_WORKER_BATCH_LIMIT`.

Nach einer Migration wird der Suchindex automatisch durch `python -m app.workers.search_main` aufgebaut. Docker Compose startet diesen Prozess als `search-worker`.

## Entity Recognition & Topic Detection

`python -m app.workers.entity_topic_main` analyzes normalized articles asynchronously with the deterministic, versioned `local-rules` provider. Results are available through `/articles/{id}/entities`, `/articles/{id}/topics`, `/entities`, and `/topics`; `/search` additionally accepts `entity_id`, typed `entity_type`, `topic_id`, and `topic_slug`.

Configure the worker with `ENTITY_TOPIC_WORKER_POLL_INTERVAL_SECONDS`, `ENTITY_TOPIC_WORKER_BATCH_LIMIT`, `ENTITY_TOPIC_WORKER_CLAIM_TTL_SECONDS`, `ENTITY_TOPIC_RETRY_BASE_SECONDS`, `ENTITY_TOPIC_RETRY_MAX_SECONDS`, `ENTITY_TOPIC_MAX_TOPICS_PER_ARTICLE`, `ENTITY_TOPIC_MIN_ENTITY_CONFIDENCE`, and `ENTITY_TOPIC_MIN_TOPIC_CONFIDENCE`. Claims are durable leases; failed articles use bounded exponential backoff. The provider contract contains no SQLAlchemy types, so external NLP/LLM providers can replace the baseline without changing persistence. The baseline is intentionally conservative: it has no coreference or knowledge-graph linking and limited location/event vocabularies. See [ADR 0009](docs/decisions/0009-entity-topic-detection.md).

Entity aliases use indexed normalized rows rather than JSONB scans. Ambiguous aliases are deliberately unresolved. Entity/topic creation is concurrency-safe through PostgreSQL upserts, and topic slug collisions receive a deterministic hash suffix. Mention offsets are zero-based Unicode code-point offsets with an exclusive end, relative to the returned `text_source` (`title` or `body`).

## Claim Extraction

`python -m app.workers.claim_main` extracts article-scoped factual claims from eligible normalized articles. The baseline `local-rules` provider is deterministic and conservative; it stores exact normalized-field spans, confidence and processing provenance without pretending to perform cross-source semantic claim matching.

Current claims are available through `/articles/{id}/claims`, `/claims/{claim_id}`, and `/stories/{story_id}/claims`. Reprocessing soft-deletes superseded claim rows and writes a new auditable generation linked to the generic `ArticleProcessingRun`. Provider failures and stale inputs preserve the last successful active claims. See [ADR 0012](docs/decisions/0012-claim-extraction.md).

## Perspective Attribution

`python -m app.workers.perspective_main` attributes active article claims to explicit known entity mentions where the normalized text provides supported reporting evidence. Results are classified as `quoted`, `reported`, or `unattributed`; this stage does not infer political ideology, truth, agreement, contradiction or source bias.

Current perspectives are available through `/articles/{id}/perspectives`, `/claims/{claim_id}/perspectives`, and `/stories/{story_id}/perspectives`. The processing identity includes the complete active claim and entity-mention generations, and finalization locks and revalidates both upstream inputs before replacing the previous active perspective generation. See [ADR 0013](docs/decisions/0013-perspective-attribution.md).

## Cross-Source Claim Groups & Relations

`python -m app.workers.claim_relation_main` groups active claims within each story into story-scoped semantic claim groups and records explicit contradictions between groups. Agreement is represented by multiple current claims and independent sources in one group rather than pairwise agreement edges. The deterministic baseline uses conservative lexical overlap, explicit negation and numeric compatibility; it does not assess truth, evidence quality or consensus.

Current results are available through `/stories/{id}/claim-groups`, `/claim-groups/{id}`, and `/stories/{id}/claim-relations`. Story-scoped durable processing leases and finalization locks coordinate with story clustering and claim extraction. See [ADR 0014](docs/decisions/0014-cross-source-claim-relations.md).


## Evidence Analysis

`python -m app.workers.evidence_main` classifies traceable evidence attached to the current story claim-group generation. Evidence types include primary sources, official data, studies, direct quotes, press releases, independent reporting and contextual material. Evidence links use `supports` or `context`; they do not represent a truth score or a verdict on factual correctness.

Current evidence is available through `/stories/{id}/evidence` and `/claim-groups/{id}/evidence`. The processing identity includes the active claim-group generation and all article/source inputs used by the evidence provider. See [ADR 0015](docs/decisions/0015-evidence-analysis.md).

## Consensus & Differences

`python -m app.workers.consensus_main` derives structural agreement and contradiction summaries from the current claim-group and evidence generations. Shared consensus requires the same claim group to be represented by at least two independent source owners. Article count alone is never treated as consensus, and no truth score is produced.

Current results are available through `/stories/{id}/consensus` and `/stories/{id}/differences`. See [ADR 0016](docs/decisions/0016-consensus-differences.md).

## Coverage Gaps & Missing Perspectives

`python -m app.workers.coverage_main` derives source/signal coverage distributions and conservative gap markers from the current Consensus generation. It reports limited independent content-source coverage, signal-only attention, and claim groups without attributed perspectives. It does not invent ideological camps or assign a coverage/truth score.

Current results are available through `/stories/{id}/coverage`, `/stories/{id}/coverage-gaps`, and `/stories/{id}/missing-perspectives`. See [ADR 0017](docs/decisions/0017-coverage-gaps.md).

## Integrated Story Analysis

`GET /stories/{id}/analysis` exposes one generation-consistent Story/Debate analysis view. It composes current Claim Groups and members, Evidence, Consensus, Differences, Coverage Gaps and Missing Perspectives and includes the processing-run IDs used for each analysis generation. The endpoint never mixes stale generations; when a complete current view is unavailable it returns 404 rather than returning partial analysis.

See [ADR 0018](docs/decisions/0018-integrated-story-analysis-api.md).

## Web Frontend

The `frontend/` application is a Next.js App Router UI for Search, Story discovery, Story detail and the integrated Story Analysis API. Server Components call FastAPI through `FSC_API_URL`, so browsers do not need direct backend/CORS access. Analysis pages deliberately display only descriptive backend results and never derive their own truth, credibility or political scores.

Local development:

```sh
cd frontend
npm install
FSC_API_URL=http://localhost:8000 npm run dev
```

Docker Compose builds the standalone Next.js image and exposes it on port `3000`.

For a CI-friendly PostgreSQL run from the repository root:

```sh
docker compose -f infrastructure/docker/docker-compose.yml up -d postgres
docker compose -f infrastructure/docker/docker-compose.yml exec postgres createdb -U "$DATABASE_USER" fsc_test
docker compose -f infrastructure/docker/docker-compose.yml run --rm -e DATABASE_NAME=fsc_test backend alembic upgrade head
docker compose -f infrastructure/docker/docker-compose.yml run --rm -e DATABASE_NAME=fsc_test backend pytest -q
```
