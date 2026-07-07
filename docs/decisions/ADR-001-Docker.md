# ADR-001: Docker Compose als Deployment-Basis

## Status

Accepted

## Entscheidung

FSC verwendet Docker Compose als Deployment-Basis.

## Begründung

Docker Compose ermöglicht eine saubere Trennung der Dienste:

- nginx
- frontend
- backend
- worker
- postgres
- redis

Die Architektur bleibt dadurch portabel, reproduzierbar und später leichter auf größere Server migrierbar.

## Konsequenzen

Alle Dienste werden containerisiert betrieben.

Konfiguration erfolgt über Umgebungsvariablen und `.env`-Dateien.

Persistente Daten werden über Docker Volumes verwaltet.
