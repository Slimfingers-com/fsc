import re
import unicodedata


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[^\w\s&+.-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip(" .-").casefold()


def stable_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", normalize_name(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-") or "topic"


def normalize_topic(value: str) -> str:
    normalized = normalize_name(value)
    words = normalized.split()
    # Conservative deterministic stemming for common plural forms.
    if words and len(words[-1]) > 4:
        if words[-1].endswith("ies"):
            words[-1] = words[-1][:-3] + "y"
        elif words[-1].endswith("en") and len(words[-1]) > 6:
            words[-1] = words[-1][:-2]
        elif words[-1].endswith("s") and not words[-1].endswith("ss"):
            words[-1] = words[-1][:-1]
    return " ".join(words)
