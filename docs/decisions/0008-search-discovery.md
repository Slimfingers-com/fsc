# ADR 0008: PostgreSQL-backed Search & Discovery

## Status
Accepted

## Decision
FSC maintains a denormalized `SearchDocument` for every normalized article. A versioned builder copies stable article and source metadata into the document and computes a deterministic document hash over every searchable or filterable field. A polling reindex worker selects missing, stale, soft-deleted, or older-version documents with `FOR UPDATE SKIP LOCKED` and updates them within one transaction per batch. Search documents are reproducible infrastructure and are hard-deleted when their article, feed, or source becomes ineligible.

Search is exposed behind a persistence-agnostic `SearchProvider` interface. The initial provider owns its SQLAlchemy session and uses PostgreSQL full text search with a stored, weighted `tsvector` and a GIN index. Titles have weight A and article bodies weight B; matching excerpts use `ts_headline`. The API supports web-style search syntax, relevance or publication-date sorting, source/language/date filters, and offset pagination with a total count. An empty query provides chronological discovery over the same filters.

## Consequences
- Search does not couple request latency to article/source joins or normalization.
- Reindexing is idempotent, versioned, and horizontally safe.
- PostgreSQL remains the only required search infrastructure.
- A future external provider can implement the same interface without changing the API contract.
- The generated vector uses the language-neutral `simple` configuration so multilingual documents remain discoverable without incorrect stemming.
