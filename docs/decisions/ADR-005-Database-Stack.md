# ADR-005 Database Stack

Status: Accepted

## Entscheidung

FSC verwendet:

- PostgreSQL
- SQLAlchemy 2.x
- psycopg3
- Alembic
- synchrones Datenbankmodell

## Begründung

Die Kombination ist stabil, weit verbreitet und für die erwartete Last von FSC mehr als ausreichend.

Komplexität durch Async-Datenbankzugriffe wird bewusst vermieden.

## Konsequenzen

Alle Datenbankzugriffe erfolgen zunächst synchron.

Eine spätere Umstellung einzelner Komponenten bleibt möglich.
