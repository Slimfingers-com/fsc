# ADR 0007: Versioned article content normalization

## Status
Accepted

## Decision
Raw feed fields remain immutable ingestion inputs. Derived content is stored separately on `Article` as normalized title and text, ISO language code, word count, reading time, SHA-256 content hash, normalization version and timestamp.

A dedicated polling worker processes articles whose normalization version is missing or older than the current implementation version. Rows are selected with `FOR UPDATE SKIP LOCKED`, allowing safe horizontal worker scaling.

## Consequences
- Reprocessing after algorithm changes is explicit and reproducible.
- Raw source data remains available for debugging and future extraction improvements.
- Downstream classification can rely on stable normalized fields and hashes.
- Language detection is deterministic through a fixed detector seed.
