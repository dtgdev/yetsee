from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from app.core.config import settings
from app.signal_engine.contracts import ConnectorManifest, FetchPage, ObservationInput, RawItem


class RedditConnector:
    API = "https://www.reddit.com/search.json"

    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            id="reddit",
            version="1.0.0",
            description="Public Reddit search observations for configured investigation topics.",
            schedule="30m",
            supports_incremental=True,
            requires_api_key=False,
        )

    def _json(self, url: str):
        request = Request(
            url,
            headers={
                "User-Agent": settings.reddit_user_agent,
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=12) as response:  # noqa: S310 - fixed public endpoint
            return json.loads(response.read().decode("utf-8"))

    def fetch(self, cursor: str | None = None) -> FetchPage:
        cursor_epoch = float(cursor or 0)
        items: list[RawItem] = []
        newest = cursor_epoch
        for topic in settings.external_signal_topic_list:
            url = (
                f"{self.API}?q={quote_plus(topic)}&sort=new&t=month"
                f"&limit={settings.reddit_results_per_topic}&type=link"
            )
            payload = self._json(url)
            for child in payload.get("data", {}).get("children", []):
                post = child.get("data") or {}
                created = float(post.get("created_utc") or 0)
                if created <= cursor_epoch:
                    continue
                post_id = str(post.get("id") or "").strip()
                if not post_id:
                    continue
                enriched = {**post, "yetsee_query_topic": topic}
                items.append(
                    RawItem(
                        source_ref=post_id,
                        observed_at=datetime.fromtimestamp(created, tz=timezone.utc),
                        payload=enriched,
                    )
                )
                newest = max(newest, created)
        return FetchPage(items=items, next_cursor=str(newest) if newest else cursor)

    def normalize(self, raw: RawItem) -> ObservationInput:
        post = raw.payload
        topic = str(post.get("yetsee_query_topic") or post.get("title") or "").strip()
        score = float(post.get("score") or 0)
        comments = float(post.get("num_comments") or 0)
        # A stable, transparent engagement measure; raw fields remain in payload.
        value = score + comments
        return ObservationInput(
            source="reddit",
            source_ref=raw.source_ref,
            topic=topic,
            metric="discussion_engagement",
            value=value,
            observed_at=raw.observed_at,
            payload=post,
        )

    def validate(self, observation: ObservationInput) -> list[str]:
        errors: list[str] = []
        if not observation.topic:
            errors.append("reddit observation requires configured query topic")
        if not observation.source_ref:
            errors.append("reddit observation requires post id")
        return errors
