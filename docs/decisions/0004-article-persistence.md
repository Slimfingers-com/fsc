# ADR 0004: Artikelidentität und Feed-Artikel-Persistenz

## Status
Akzeptiert

## Kontext
Eine Source repräsentiert einen Anbieter und kann mehrere konkrete Feeds bereitstellen. Jeder Feed kann viele Artikel enthalten. RSS- und Atom-Einträge liefern jedoch nicht immer eine stabile GUID und können bei späteren Abrufen veränderte Inhalte enthalten.

## Entscheidung
Artikel werden unterhalb eines Feeds persistiert. Ihre Identität wird in folgender Reihenfolge bestimmt:

1. GUID bzw. externe ID
2. Link
3. abgeleiteter Wert aus Titel, Veröffentlichungszeitpunkt und Autor

Aus Identitätstyp und kanonischem Wert wird ein SHA-256-Schlüssel erzeugt. Der Datenbank-Constraint `UNIQUE(feed_id, identity_key)` garantiert Idempotenz pro Feed. GUID und Link werden zusätzlich im Klartext gespeichert, damit ein zunächst linkbasierter Artikel später auf eine verfügbare GUID hochgestuft werden kann.

Sowohl `summary` als auch `content` werden gespeichert, weil Feeds diese Felder unabhängig voneinander bereitstellen. Das externe Änderungsdatum heißt `source_updated_at`, da `updated_at` bereits als technisches Audit-Feld durch `BaseModel` belegt ist.

Der Persistenz-Service aktualisiert vorhandene Artikel, legt neue Artikel an und aktualisiert nach erfolgreicher Verarbeitung den Laufzeitzustand des Feeds. Er führt selbst keinen Commit aus; Transaktionsgrenzen bleiben beim Aufrufer.

## Konsequenzen
- Wiederholte Verarbeitung desselben Feeds ist idempotent.
- Mehrere Feeds derselben Source bleiben fachlich getrennt.
- Feed-Inhalte gehen unabhängig von späterem Web-Scraping nicht verloren.
- Repository und Service bleiben unabhängig von `feedparser`-Objekten und arbeiten ausschließlich mit den Ingestion-DTOs.
