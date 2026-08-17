import hashlib
import json
from dataclasses import asdict

from app.signal_engine.contracts import ObservationInput


def observation_hash(observation: ObservationInput) -> str:
    canonical = {
        "source": observation.source,
        "source_ref": observation.source_ref,
        "topic": observation.topic,
        "metric": observation.metric,
        "value": observation.value,
        "observed_at": observation.observed_at.isoformat(),
        "payload": observation.payload,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
