# ADR-007 Transaction and Session Strategy

Status: Accepted

## Entscheidung

FSC verwendet folgende Datenzugriffs- und Transaktionsstrategie.

### Session Lifecycle

- Eine Datenbank-Session pro Request, Job oder Kommando
- Die Session wird nach Abschluss zuverlässig geschlossen
- Bei unbehandelten Fehlern erfolgt ein Rollback

### Repository Layer

- Repositorys führen ausschließlich Datenzugriffe aus
- Repositorys führen keine Commits oder Rollbacks aus
- Repositorys dürfen `flush()` auslösen, wenn eine Operation Datenbankwerte wie UUIDs benötigt

### Service Layer

- Services enthalten Geschäftslogik
- Services führen keine Commits oder Rollbacks aus
- Services dürfen mehrere Repository-Operationen innerhalb einer gemeinsamen Transaktion ausführen
- Services verwenden `flush()`, wenn Datenbankänderungen vor dem Commit geprüft oder weiterverarbeitet werden müssen

### Transaction Boundary

- Der aufrufende Anwendungsfall kontrolliert die Transaktion
- API-Endpunkte, Worker-Jobs, Importprozesse oder Command-Handler entscheiden über Commit und Rollback
- Mehrere Service-Aufrufe können dadurch atomar in einer gemeinsamen Transaktion ausgeführt werden

### API Layer

- APIs validieren Eingaben
- APIs übersetzen Ergebnisse und Domain-Exceptions in HTTP-Antworten
- APIs enthalten keine fachliche Geschäftslogik
- APIs committen nur nach erfolgreichem Abschluss des gesamten Anwendungsfalls

### Soft Delete

- Datensätze werden grundsätzlich nicht physisch gelöscht
- Löschungen setzen `deleted_at`
- Standardabfragen filtern Datensätze mit gesetztem `deleted_at` aus

## Begründung

Die Trennung ermöglicht:

- atomare Änderungen über mehrere Services und Repositorys
- gemeinsame Transaktionen für Geschäftsänderung und Audit-Eintrag
- saubere Batch-Importe
- klare Verantwortlichkeiten
- bessere Testbarkeit
- kontrollierte Rollbacks

## Konsequenzen

Ein Service-Aufruf allein speichert Änderungen noch nicht dauerhaft.

Der Aufrufer muss nach erfolgreichem Abschluss explizit committen.

Bei Fehlern muss die gesamte Transaktion zurückgerollt werden.
