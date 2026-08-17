from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.signal_engine.contracts import ConnectorManifest, FetchPage, ObservationInput, RawItem


class GoogleTrendsConnector:
    """Google Trends interest-over-time connector using the community pytrends client.

    Google does not currently publish a supported Trends API for this use case, so this
    connector is intentionally isolated behind the Connector contract. If Google changes
    the endpoint, YetSee's evidence/investigation layers do not need to change.
    """

    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            id="google_trends",
            version="1.0.0",
            description="Google Trends interest-over-time observations for configured topics via pytrends.",
            schedule="6h",
            supports_history=True,
            supports_incremental=True,
            requires_api_key=False,
        )

    def _latest_interest(self, topic: str) -> tuple[datetime, float, dict]:
        try:
            from pytrends.request import TrendReq
        except ImportError as exc:  # pragma: no cover - dependency installed by project image
            raise RuntimeError("google_trends connector requires pytrends") from exc

        client = TrendReq(hl="en-US", tz=0, retries=2, backoff_factor=0.2)
        client.build_payload([topic], timeframe=settings.google_trends_timeframe, geo=settings.google_trends_geo)
        frame = client.interest_over_time()
        if frame is None or frame.empty or topic not in frame.columns:
            raise RuntimeError(f"Google Trends returned no interest data for {topic!r}")
        usable = frame
        if "isPartial" in usable.columns:
            complete = usable[usable["isPartial"] == False]  # noqa: E712 - pandas boolean comparison
            if not complete.empty:
                usable = complete
        row = usable.iloc[-1]
        index = usable.index[-1]
        observed_at = index.to_pydatetime() if hasattr(index, "to_pydatetime") else datetime.now(timezone.utc)
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        return observed_at, float(row[topic]), {
            "query": topic,
            "geo": settings.google_trends_geo,
            "timeframe": settings.google_trends_timeframe,
            "interest": float(row[topic]),
            "provider": "google_trends_via_pytrends",
        }

    def fetch(self, cursor: str | None = None) -> FetchPage:
        items: list[RawItem] = []
        newest = cursor
        failures: list[str] = []
        for topic in settings.external_signal_topic_list:
            try:
                observed_at, value, payload = self._latest_interest(topic)
            except Exception as exc:
                failures.append(f"{topic}: {exc}")
                continue
            source_ref = f"{settings.google_trends_geo}:{topic}:{observed_at.isoformat()}"
            items.append(
                RawItem(
                    source_ref=source_ref,
                    observed_at=observed_at,
                    payload={**payload, "value": value},
                )
            )
            newest = max(newest or "", observed_at.isoformat())
        if not items and failures:
            raise RuntimeError("; ".join(failures)[:3000])
        return FetchPage(items=items, next_cursor=newest)

    def normalize(self, raw: RawItem) -> ObservationInput:
        return ObservationInput(
            source="google_trends",
            source_ref=raw.source_ref,
            topic=str(raw.payload.get("query") or "").strip(),
            metric="search_interest",
            value=float(raw.payload.get("value") or 0),
            observed_at=raw.observed_at,
            payload=raw.payload,
        )

    def validate(self, observation: ObservationInput) -> list[str]:
        return [] if observation.topic and observation.source_ref else ["google trends observation requires topic and source reference"]
