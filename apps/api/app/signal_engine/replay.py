from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observation import Observation


def replay_observations(
    db: Session,
    *,
    start: datetime,
    end: datetime,
    source: str | None = None,
) -> list[Observation]:
    statement = select(Observation).where(
        Observation.observed_at >= start,
        Observation.observed_at <= end,
    )
    if source:
        statement = statement.where(Observation.source == source)
    return list(db.scalars(statement.order_by(Observation.observed_at.asc())))
