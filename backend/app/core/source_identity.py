import unicodedata


def normalize_source_name(value: str) -> str:
    """Normalisiert einen Quellennamen für die Dublettenprüfung."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.strip().split())

    return normalized.casefold()
