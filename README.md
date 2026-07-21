# FSC – Fair Spectrum Compass

FSC ist eine Plattform zur transparenten Analyse öffentlicher Debatten.

Ziel ist es, Ereignisse nicht nur als Nachrichten darzustellen, sondern Perspektiven, Claims, Evidenz, Konsens, Unterschiede, Coverage Gaps und fehlende Perspektiven sichtbar zu machen.

## Search & Discovery

Normalisierte Artikel werden durch einen eigenen Worker in versionierte `SearchDocument`-Datensätze überführt. `GET /search` bietet PostgreSQL-Volltextsuche sowie Discovery ohne Suchtext.

Unterstützte Parameter: `q`, `language`, `source_id`, `source`, `published_from`, `published_to`, `sort` (`relevance`, `newest`, `oldest`), `page` und `page_size`. Die Seitengröße ist über `SEARCH_DEFAULT_PAGE_SIZE` und `SEARCH_MAX_PAGE_SIZE` konfigurierbar; der Reindex-Worker über `SEARCH_WORKER_POLL_INTERVAL_SECONDS` und `SEARCH_WORKER_BATCH_LIMIT`.

Nach einer Migration wird der Suchindex automatisch durch `python -m app.workers.search_main` aufgebaut. Docker Compose startet diesen Prozess als `search-worker`.

## Entity Recognition & Topic Detection

`python -m app.workers.entity_topic_main` analyzes normalized articles asynchronously with the deterministic, versioned `local-rules` provider. Results are available through `/articles/{id}/entities`, `/articles/{id}/topics`, `/entities`, and `/topics`; `/search` additionally accepts `entity_id`, `entity_type`, `topic_id`, and `topic` (slug).

Configure the worker with `ENTITY_TOPIC_WORKER_POLL_INTERVAL_SECONDS`, `ENTITY_TOPIC_WORKER_BATCH_LIMIT`, `ENTITY_TOPIC_MAX_TOPICS_PER_ARTICLE`, `ENTITY_TOPIC_MIN_ENTITY_CONFIDENCE`, and `ENTITY_TOPIC_MIN_TOPIC_CONFIDENCE`. The provider contract contains no SQLAlchemy types, so external NLP/LLM providers can replace the baseline without changing persistence. The baseline is intentionally conservative: it has no coreference or knowledge-graph linking and limited location/event vocabularies. See [ADR 0009](docs/decisions/0009-entity-topic-detection.md).
