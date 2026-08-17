import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from app.signal_engine.contracts import ConnectorManifest, FetchPage, ObservationInput, RawItem


class HackerNewsConnector:
    API = "https://hacker-news.firebaseio.com/v0"

    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            id="hacker_news",
            version="1.0.0",
            description="Public Hacker News top-story observations.",
            schedule="15m",
            supports_incremental=True,
            requires_api_key=False,
        )

    def _json(self, url: str):
        request = Request(url, headers={"User-Agent": "YetSee/0.2 SignalLake"})
        with urlopen(request, timeout=8) as response:  # noqa: S310 - fixed public endpoint
            return json.loads(response.read().decode("utf-8"))

    def fetch(self, cursor: str | None = None) -> FetchPage:
        ids = self._json(f"{self.API}/topstories.json")[:20]
        items: list[RawItem] = []
        newest = cursor
        for item_id in ids:
            item = self._json(f"{self.API}/item/{item_id}.json")
            if not item or item.get("type") != "story" or not item.get("title"):
                continue
            observed_at = datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)
            items.append(RawItem(source_ref=str(item_id), observed_at=observed_at, payload=item))
            newest = str(max(int(newest or 0), int(item_id)))
        return FetchPage(items=items, next_cursor=newest)

    def normalize(self, raw: RawItem) -> ObservationInput:
        title = str(raw.payload.get("title", "")).strip()
        return ObservationInput(
            source="hacker_news",
            source_ref=raw.source_ref,
            topic=title,
            metric="story_score",
            value=float(raw.payload.get("score", 0)),
            observed_at=raw.observed_at,
            payload=raw.payload,
        )

    def validate(self, observation: ObservationInput) -> list[str]:
        return [] if observation.topic and observation.source_ref else ["story requires title and id"]
