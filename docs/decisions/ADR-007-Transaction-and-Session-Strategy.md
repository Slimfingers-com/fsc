# ADR-007 Transaction and Session Strategy

Status: Accepted

## Entscheidung

FSC verwendet folgende Datenzugriffs- und Transaktionsstrategie.

### Session Lifecycle

- Eine Datenbank-Session pro Request, Job oder Kommando
- Die Session wird nach Abschluss zuverlässig geschlossen
- Bei unbehandelten Fehlern erfolgt ein Rollback
- Worker verwenden für claimende und verarbeitende Transaktionen dieselbe fachliche Session nur dann weiter, wenn der Zustand vor jeder Verarbeitung explizit aus der Datenbank aktualisiert wird

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

### Durable Article Processing

Die generische Article-Processing-Infrastruktur behandelt einen Claim nicht nur als Besitzrecht, sondern als Snapshot einer vollständigen Processing-Identity. Ein Claim enthält Input-Hash, Provider, Provider-Version und Konfigurations-Version. Nach dem Claim-Commit darf ein Worker nur genau diese Identität erfolgreich abschließen.

Vor einer mutierenden Verarbeitung wird der aktuelle `Article` mit `populate_existing` und, sofern die Pipeline den Artikel selbst verändert oder von einem stabilen Snapshot abhängt, mit `SELECT ... FOR UPDATE OF Article` neu gelesen. Der aktuelle Candidate wird gegen den Claim verglichen. Hat sich die Identität geändert, wird der Run als `skipped` beendet und bleibt für einen neuen Claim mit dem aktuellen Input verfügbar.

Pipelines, die einen externen oder außerhalb der finalen Schreibtransaktion laufenden Provider verwenden, prüfen die Identität zusätzlich unmittelbar vor der Persistierung des Provider-Ergebnisses. Dadurch kann ein Ergebnis für Input A nicht als Verarbeitung von Input B committed werden.

Lease- und Fachlocks werden vor den fachlichen Writes in einer festen Reihenfolge genommen. Ein verlorener Lease darf keine fachlichen Änderungen committen. Reprocessing ersetzt reproduzierbare Derived-Daten atomar und lässt die letzte erfolgreiche Version nur dort bestehen, wo die jeweilige ADR dies ausdrücklich vorsieht.

### API Layer

- APIs validieren Eingaben
- APIs übersetzen Ergebnisse und Domain-Exceptions in HTTP-Antworten
- APIs enthalten keine fachliche Geschäftslogik
- APIs committen nur nach erfolgreichem Abschluss des gesamten Anwendungsfalls

### Soft Delete

- Datensätze werden grundsätzlich nicht physisch gelöscht
- Löschungen setzen `deleted_at`
- Standardabfragen filtern Datensätze mit gesetztem `deleted_at` aus
- Derived-Daten dürfen nicht sichtbar oder als Features verwendet werden, wenn ihr Article, Feed, ihre Source oder ihre Zuordnung inaktiv bzw. soft-gelöscht ist

## Begründung

Die Trennung ermöglicht:

- atomare Änderungen über mehrere Services und Repositorys
- gemeinsame Transaktionen für Geschäftsänderung und Audit-Eintrag
- saubere Batch-Importe
- klare Verantwortlichkeiten
- bessere Testbarkeit
- kontrollierte Rollbacks
- reproduzierbares Reprocessing ohne Stale-Claim-Races

## Konsequenzen

Ein Service-Aufruf allein speichert Änderungen noch nicht dauerhaft.

Der Aufrufer muss nach erfolgreichem Abschluss explizit committen.

Bei Fehlern muss die gesamte Transaktion zurückgerollt werden.

Worker müssen Claim-Identity, Lease und den tatsächlich persistierten Input als eine gemeinsame Korrektheitsinvariante behandeln.
