from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.feature_engine.registry import registry
from app.models.feature import Feature, FeatureRun
from app.models.observation import Observation


def recompute_features(db: Session, hours: int = 24 * 30) -> dict:
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    observations = list(db.scalars(select(Observation).where(Observation.observed_at >= start).order_by(Observation.observed_at)))
    run_ids: list[str] = []
    feature_count = 0
    for extractor in registry.all():
        manifest = extractor.manifest()
        run = FeatureRun(
            extractor_id=manifest.id,
            extractor_version=manifest.version,
            status="running",
            started_at=datetime.now(timezone.utc),
            observation_count=len(observations),
            metadata_json={"window_hours": hours},
        )
        db.add(run)
        db.flush()
        try:
            extracted = extractor.extract(observations)
            now = datetime.now(timezone.utc)
            for item in extracted:
                db.add(Feature(
                    subject=item.subject,
                    feature_type=item.feature_type,
                    name=item.name,
                    value=item.value,
                    vector=item.vector,
                    window=item.window,
                    extractor_id=manifest.id,
                    extractor_version=manifest.version,
                    confidence=item.confidence,
                    evidence_ids=item.evidence_ids,
                    attributes={**item.attributes, "feature_run_id": run.id, "window_hours": hours},
                    computed_at=now,
                ))
            run.feature_count = len(extracted)
            run.status = "succeeded"
            feature_count += len(extracted)
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:4000]
        run.finished_at = datetime.now(timezone.utc)
        run_ids.append(run.id)
    db.commit()
    return {"observations": len(observations), "feature_runs": run_ids, "features_created": feature_count}


def latest_features(db: Session, subject: str | None = None, feature_type: str | None = None, limit: int = 200):
    statement = select(Feature)
    if subject:
        statement = statement.where(Feature.subject.ilike(f"%{subject}%"))
    if feature_type:
        statement = statement.where(Feature.feature_type == feature_type)
    return list(db.scalars(statement.order_by(Feature.computed_at.desc()).limit(limit)))
