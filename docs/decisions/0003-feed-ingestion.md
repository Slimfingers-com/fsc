# ADR 0003: Feed-Ingestion als eigenständiges Anwendungspaket

## Status
Akzeptiert

## Entscheidung
Die vollständige Feed-Aufnahme wird unter `app.ingestion` gebündelt.

- `fetcher.py`: HTTP-Abruf und Conditional GET
- `parser.py`: RSS-/Atom-Parsing und Normalisierung
- `models.py`: unveränderliche DTOs
- `exceptions.py`: Ingestion-spezifische Fehler
- `__init__.py`: öffentliche Paketoberfläche

Der Fetcher kennt keine Persistenz. Der Parser kennt keinen HTTP-Client.
`feedparser` bleibt hinter `FeedParser` gekapselt.
