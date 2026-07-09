# ADR-006 Entity Identity Strategy

Status: Accepted

## Entscheidung

FSC verwendet für alle Kernobjekte UUIDs als Primärschlüssel.

Alle Kernobjekte erhalten standardmäßig:

- id
- created_at
- updated_at
- deleted_at

## Begründung

UUIDs erleichtern spätere Skalierung, Importe, Exporte und verteilte Verarbeitung.

Zeitstempel ermöglichen Nachvollziehbarkeit.

Soft Deletes über `deleted_at` verhindern, dass wichtige historische Informationen versehentlich verloren gehen.

## Konsequenzen

Kernobjekte werden nicht physisch gelöscht, sondern über `deleted_at` deaktiviert.

Die Anwendung filtert gelöschte Objekte standardmäßig aus.

Physische Löschung bleibt nur für technische Wartung oder rechtliche Sonderfälle vorgesehen.
