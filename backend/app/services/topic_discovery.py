import re
from collections import Counter, defaultdict
from app.connectors.base import Observation

STOPWORDS = {
    "about","after","again","against","also","and","are","because","been","before","being","between","but","can","could",
    "from","have","into","its","more","most","new","not","now","over","said","says","that","the","their","them","there","they",
    "this","through","today","under","using","was","were","what","when","where","which","while","who","why","will","with","would",
    "you","your","how","for","has","had","our","out","all","than","just","first","here","gets","get","may","one","two","on","in","of","to","a","an","is","as","at","by","or"
}


def _tokens(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", text.lower()) if w not in STOPWORDS]


def discover_topics(observations: list[Observation], limit: int = 6) -> list[dict]:
    phrase_counts: Counter[str] = Counter()
    phrase_sources: dict[str, set[str]] = defaultdict(set)
    phrase_observations: dict[str, list[Observation]] = defaultdict(list)

    for obs in observations:
        words = _tokens(obs.title)
        candidates = words + [" ".join(words[i:i+2]) for i in range(len(words)-1)]
        seen: set[str] = set()
        for phrase in candidates:
            if phrase in seen or len(phrase) < 4:
                continue
            seen.add(phrase)
            phrase_counts[phrase] += 1
            phrase_sources[phrase].add(obs.source)
            phrase_observations[phrase].append(obs)

    ranked = []
    for phrase, count in phrase_counts.items():
        source_count = len(phrase_sources[phrase])
        if count < 2 and source_count < 2:
            continue
        score = count + source_count * 1.5 + (0.5 if " " in phrase else 0)
        ranked.append((score, phrase))
    ranked.sort(reverse=True)

    chosen: list[dict] = []
    used_words: set[str] = set()
    for score, phrase in ranked:
        words = set(phrase.split())
        if words and words.issubset(used_words):
            continue
        chosen.append({
            "topic": phrase,
            "score": score,
            "sources": sorted(phrase_sources[phrase]),
            "observations": phrase_observations[phrase][:12],
        })
        used_words.update(words)
        if len(chosen) >= limit:
            break
    return chosen
