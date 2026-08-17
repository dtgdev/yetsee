import asyncio
import logging
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.live_discovery import run_live

log = logging.getLogger("yetsee.scheduler")


async def discovery_scheduler():
    if not settings.auto_discovery_enabled:
        return
    await asyncio.sleep(settings.auto_discovery_initial_delay_seconds)
    while True:
        db = SessionLocal()
        try:
            result = await run_live(db)
            log.info("scheduled discovery completed: %s", result)
        except Exception:
            log.exception("scheduled discovery failed")
        finally:
            db.close()
        await asyncio.sleep(settings.auto_discovery_interval_seconds)
