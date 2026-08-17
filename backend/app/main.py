import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.services.scheduler import discovery_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(discovery_scheduler()) if settings.auto_discovery_enabled else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Opportunity Intelligence Platform",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/")
def root():
    return {"name": "YetSee", "tagline": "See What's Next.", "version": settings.app_version}


@app.get("/health")
def health():
    return {"status": "ok", "auto_discovery": settings.auto_discovery_enabled}
