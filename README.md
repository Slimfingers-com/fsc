# FSC – Fair Spectrum Compass

FSC ist eine Plattform zur transparenten Analyse öffentlicher Debatten.

Ziel ist es, Ereignisse nicht nur als Nachrichten darzustellen, sondern Perspektiven, Claims, Evidenz, Konsens, Unterschiede, Coverage Gaps und fehlende Perspektiven sichtbar zu machen.

## Search & Discovery

Normalisierte Artikel werden durch einen eigenen Worker in versionierte `SearchDocument`-Datensätze überführt. `GET /search` bietet PostgreSQL-Volltextsuche sowie Discovery ohne Suchtext.

Unterstützte Parameter: `q`, `language`, `source_id`, `source`, `published_from`, `published_to`, `sort` (`relevance`, `newest`, `oldest`), `page` und `page_size`. Die Seitengröße ist über `SEARCH_DEFAULT_PAGE_SIZE` und `SEARCH_MAX_PAGE_SIZE` konfigurierbar; der Reindex-Worker über `SEARCH_WORKER_POLL_INTERVAL_SECONDS` und `SEARCH_WORKER_BATCH_LIMIT`.

Nach einer Migration wird der Suchindex automatisch durch `python -m app.workers.search_main` aufgebaut. Docker Compose startet diesen Prozess als `search-worker`.
