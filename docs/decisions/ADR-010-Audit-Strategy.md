# ADR-010 Audit Strategy

Status: Accepted

## Entscheidung

FSC führt fachliche Änderungen über ein zentrales Audit Log nach.

Audit-Einträge werden nicht durch Repositorys erzeugt.

Audit-Einträge werden durch Services innerhalb derselben Transaktion erzeugt.

## Ziele

Nachvollziehbarkeit von:

- Erstellung
- Änderung
- Deaktivierung
- Reaktivierung
- Archivierung

von fachlichen Objekten.

## Nicht-Ziele

Keine Speicherung von:

- Passwörtern
- API Keys
- Tokens
- Secrets

## Audit Prinzip

Geschäftsänderung und Audit-Eintrag gehören zur selben Transaktion.

Entweder:

- Änderung und Audit erfolgreich

oder

- beides Rollback

## Geplante Struktur

AuditLog

- entity_type
- entity_id
- action
- actor_type
- actor_id
- source
- old_values
- new_values
- created_at

## Actor Types

- USER
- SYSTEM
- IMPORTER
- WORKER

## Actions

- CREATE
- UPDATE
- ACTIVATE
- DEACTIVATE
- DELETE
