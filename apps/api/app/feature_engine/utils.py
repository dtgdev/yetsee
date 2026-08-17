import hashlib
import math
import re
from collections import Counter


def normalize_topic(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", value.lower())).strip()


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def hashed_embedding(text: str, dimensions: int = 24) -> list[float]:
    """Deterministic dependency-light semantic fingerprint.

    This is intentionally replaceable by a production embedding model later.
    """
    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    counts = Counter(tokens)
    for token, count in counts.items():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        slot = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[slot] += sign * float(count)
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]
