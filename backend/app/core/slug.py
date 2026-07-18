import re
import unicodedata


def generate_slug(value: str) -> str:
    """Erzeugt einen URL-tauglichen Slug aus einem Namen."""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")

    slug = ascii_value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return slug
