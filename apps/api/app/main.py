from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.graph_projection_routes import router as graph_projection_router
from app.api.mission_routes import router as mission_router
from app.api.routes import router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.9.0-alpha",
    description="YetSee OS Alpha - reference implementation of investigation-centric computing",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "YetSee",
        "tagline": "See What's Next.",
        "phase": "YetSee OS Alpha - Intelligence Kernel",
    }


app.include_router(router, prefix=settings.api_v1_prefix)
app.include_router(graph_projection_router, prefix=settings.api_v1_prefix, tags=["graph-projections"])
app.include_router(mission_router, prefix=settings.api_v1_prefix, tags=["missions"])
