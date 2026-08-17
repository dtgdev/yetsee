import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceLink
from app.models.investigation import Investigation
from app.models.observation import Observation

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def investigation_bundle(db: Session, investigation_id: str):
    investigation = db.get(Investigation, investigation_id)
    if investigation is None:
        raise KeyError(investigation_id)
    links = list(db.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id)))
    observation_ids = [link.observation_id for link in links if link.observation_id]
    observations = list(db.scalars(select(Observation).where(Observation.id.in_(observation_ids)))) if observation_ids else []
    return investigation, links, observations
