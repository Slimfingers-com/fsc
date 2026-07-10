# ADR-007 Transaction and Session Strategy

Status: Accepted

## Entscheidung

FSC verwendet folgende Datenzugriffsstrategie:

### Session Lifecycle

- Eine Datenbank-Session pro Request
- Die Session wird nach Abschluss des Requests geschlossen

### Repository Layer

- Repositorys führen ausschließlich Datenzugriffe aus
- Repositorys führen keine Commits oder Rollbacks aus

### Service Layer

- Services enthalten Geschäftslogik
- Services sind für Commit und Rollback verantwortlich

### API Layer

- APIs validieren Eingaben
- APIs übersetzen Ergebnisse in HTTP-Antworten
- APIs enthalten keine Geschäftslogik

### Soft Delete

- Datensätze werden grundsätzlich nicht physisch gelöscht
- Löschungen setzen `deleted_at`
- Standardabfragen filtern Datensätze mit gesetztem `deleted_at` aus

## Begründung

Diese Trennung ermöglicht:

- klare Verantwortlichkeiten
- konsistente Transaktionen
- bessere Testbarkeit
- spätere Erweiterbarkeit

## Konsequenzen

Repositorys bleiben einfach und wiederverwendbar.

Komplexe Vorgänge können mehrere Repository-Operationen innerhalb einer gemeinsamen Transaktion ausführen.

Historische Daten bleiben nachvollziehbar.
