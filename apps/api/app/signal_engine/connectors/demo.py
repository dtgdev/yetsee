from datetime import datetime, timezone

from app.signal_engine.contracts import ConnectorManifest, FetchPage, ObservationInput, RawItem


class DemoConnector:
    def manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            id="demo",
            version="1.0.0",
            description="Deterministic connector used to validate the Signal Lake pipeline.",
            schedule="manual",
            supports_history=True,
        )

    def fetch(self, cursor: str | None = None) -> FetchPage:
        now = datetime.now(timezone.utc)
        rows = [
            ("running-clubs-search", "running clubs", "search_interest", 52.0),
            ("running-clubs-community", "running clubs", "community_velocity", 44.0),
            ("home-battery-search", "home batteries", "search_interest", 31.0),
            ("ai-agents-jobs", "ai agents", "job_demand", 38.0),
        ]
        items = [
            RawItem(
                source_ref=ref,
                observed_at=now,
                payload={"topic": topic, "metric": metric, "value": value, "demo": True},
            )
            for ref, topic, metric, value in rows
        ]
        return FetchPage(items=items, next_cursor=now.isoformat())

    def normalize(self, raw: RawItem) -> ObservationInput:
        return ObservationInput(
            source="demo",
            source_ref=raw.source_ref,
            topic=str(raw.payload["topic"]),
            metric=str(raw.payload["metric"]),
            value=float(raw.payload["value"]),
            observed_at=raw.observed_at,
            payload=raw.payload,
        )

    def validate(self, observation: ObservationInput) -> list[str]:
        errors: list[str] = []
        if not observation.metric:
            errors.append("metric is required")
        if observation.observed_at.tzinfo is None:
            errors.append("observed_at must include timezone")
        return errors
