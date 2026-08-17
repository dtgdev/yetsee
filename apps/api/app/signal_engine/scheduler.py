"""Minimal scheduler entrypoint.

Run with `python -m app.signal_engine.scheduler`. The production scheduler can later
move to Temporal/Celery without changing connector or ingestion contracts.
"""
import os
import time

from app.db.session import SessionLocal
from app.signal_engine.ingestion import run_all_connectors


def main() -> None:
    interval = int(os.getenv("YETSEE_INGEST_INTERVAL_SECONDS", "900"))
    while True:
        with SessionLocal() as db:
            run_all_connectors(db)
        time.sleep(interval)


if __name__ == "__main__":
    main()
