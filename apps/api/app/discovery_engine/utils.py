import math
import re
from collections import Counter
from datetime import datetime, timezone

from app.models.observation import Observation

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "into", "over", "under", "after",
    "before", "about", "your", "their", "they", "will", "have", "has", "had", "are", "was",
    "were", "news", "video", "world", "years", "support", "today", "new", "says", "more",
}


def normalize_topic(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", value.lower())).strip()


def tokens(value: str | None) -> set[str]:
    return {token for token in normalize_topic(value).split() if len(token) > 2 and token not in STOPWORDS}


def age_hours(observation: Observation) -> float:
    now = datetime.now(timezone.utc)
    observed = observation.observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return max(0.0, (now - observed).total_seconds() / 3600.0)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def topic_counts(observations: list[Observation]) -> Counter[str]:
    return Counter(normalize_topic(item.topic) for item in observations if normalize_topic(item.topic))


def recency_weight(hours: float, half_life: float = 72.0) -> float:
    return math.exp(-math.log(2) * hours / half_life)
