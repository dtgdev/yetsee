import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedEntity:
    canonical_name: str
    canonical_key: str
    kind: str
    aliases: tuple[str, ...] = ()


CATALOG: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "openai": ("OpenAI", "company", ("open ai",)),
    "anthropic": ("Anthropic", "company", ()),
    "nvidia": ("NVIDIA", "company", ("nvda",)),
    "stripe": ("Stripe", "company", ()),
    "openrouter": ("OpenRouter", "company", ("open router",)),
    "cloudflare": ("Cloudflare", "company", ()),
    "firefox": ("Firefox", "product", ()),
    "claude": ("Claude", "product", ()),
    "risc v": ("RISC-V", "technology", ("risc-v", "riscv")),
    "ai agents": ("AI Agents", "technology", ("ai agent", "agentic ai", "autonomous agents")),
    "running clubs": ("Running Clubs", "behavior", ("run clubs", "social running", "running club")),
    "home batteries": ("Home Batteries", "product_category", ("home battery", "residential batteries")),
}


def canonicalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def resolve_phrase(value: str, default_kind: str = "topic") -> ResolvedEntity:
    key = canonicalize(value)
    for catalog_key, (name, kind, aliases) in CATALOG.items():
        candidates = {catalog_key, *(canonicalize(alias) for alias in aliases)}
        if key in candidates:
            return ResolvedEntity(name, canonicalize(name), kind, aliases)
    return ResolvedEntity(value.strip().title(), key, default_kind, ())


def extract_known_entities(text: str) -> list[ResolvedEntity]:
    normalized = f" {canonicalize(text)} "
    found: dict[str, ResolvedEntity] = {}
    for catalog_key, (name, kind, aliases) in CATALOG.items():
        candidates = [catalog_key, *aliases]
        if any(f" {canonicalize(candidate)} " in normalized for candidate in candidates):
            entity = ResolvedEntity(name, canonicalize(name), kind, aliases)
            found[entity.canonical_key] = entity
    return list(found.values())
