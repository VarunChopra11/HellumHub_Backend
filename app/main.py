from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.api.routers.smart_switch import firmware_router, router as smart_switch_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.indexes import ensure_indexes
from app.db.mongo import mongo_state
from app.middleware.rate_limit import PathRateLimiterMiddleware
from app.middleware.request_context import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings

    await mongo_state.connect(settings)
    await ensure_indexes(mongo_state.db, settings.gridfs_bucket_name)
    yield
    await mongo_state.close()


def create_app(*, enable_lifespan: bool = True) -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan if enable_lifespan else None)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-Id"],
        )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        PathRateLimiterMiddleware,
        limit=settings.check_rate_limit,
        path="/smart_switch/check",
    )

    app.include_router(health_router)
    app.include_router(smart_switch_router)
    app.include_router(firmware_router)
    app.include_router(admin_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    environment = settings.environment.lower()
    host = "localhost" if environment == "dev" else "0.0.0.0"
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = environment == "dev"

    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)
