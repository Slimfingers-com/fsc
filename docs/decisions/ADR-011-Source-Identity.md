# ADR-011 Source Identity

Status: Accepted

## Entscheidung

FSC trennt bei Quellen zwischen Anzeigename, URL-Kennung und fachlicher Identität.

### name

Der Anzeigename der Quelle.

Beispiel:

Reuters

### slug

Eine stabile, URL-taugliche Kennung.

Beispiel:

reuters

Der Slug wird beim Anlegen erzeugt und danach nicht automatisch geändert.

### normalized_name

Eine normalisierte Vergleichsform des Quellennamens.

Beispiel:

Reuters
reuters
REUTERS
 ReUtErS

werden alle zu:

reuters

`normalized_name` ist eindeutig.

## Begründung

Eine einfache Eindeutigkeit auf `name` reicht nicht aus, weil PostgreSQL Groß- und Kleinschreibung unterscheidet.

`normalized_name` verhindert fachliche Dubletten, ohne unterschiedliche Quellen wie „Reuters“ und „Reuters Graphics“ vorschnell zusammenzuführen.

## Konsequenzen

- `name` bleibt der sichtbare Originalname.
- `slug` dient stabilen URLs.
- `normalized_name` dient der Dublettenprüfung.
- Die Datenbank erhält einen Unique Constraint auf `normalized_name`.
- Die Normalisierung erfolgt zentral im Service.
