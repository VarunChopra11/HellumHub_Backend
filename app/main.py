from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers.admin import router as admin_router
from app.api.routers.admin_roles import router as admin_roles_router
from app.api.routers.consumer import router as consumer_router
from app.api.routers.device_models import router as device_models_router
from app.api.routers.health import router as health_router
from app.api.routers.oauth import router as oauth_router
from app.api.routers.smart_home import router as smart_home_router
from app.api.routers.smart_switch import firmware_router, router as smart_switch_router
from app.api.routers.smarthome_admin import router as smarthome_admin_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.indexes import ensure_indexes
from app.db.mongo import mongo_state
from app.middleware.rate_limit import PathRateLimiterMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.services.mqtt_service import mqtt_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.settings = settings

    # -------------------------------------------------------------------------
    # MongoDB — connect and ensure indexes
    # -------------------------------------------------------------------------
    await mongo_state.connect(settings)
    await ensure_indexes(mongo_state.db, settings.gridfs_bucket_name)

    # -------------------------------------------------------------------------
    # MQTT Bridge — start background listener task
    # Configure the singleton with settings from env before starting.
    # -------------------------------------------------------------------------
    mqtt_service._host = settings.mqtt_broker_host
    mqtt_service._port = settings.mqtt_broker_port
    await mqtt_service.start(mongo_state.db)

    yield

    # -------------------------------------------------------------------------
    # Shutdown — stop MQTT bridge then close MongoDB
    # -------------------------------------------------------------------------
    await mqtt_service.stop()
    await mongo_state.close()


def create_app(*, enable_lifespan: bool = True) -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Hellum IoT Core Backend",
        description=(
            "Unified backend for OTA firmware updates and Smart Home device control. "
            "Bridges Google Home to ESP32 smart switchboards via MQTT."
        ),
        version="2.0.0",
        lifespan=lifespan if enable_lifespan else None,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
        )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        PathRateLimiterMiddleware,
        limit=settings.check_rate_limit,
        path="/smart_switch/check",
    )

    # -------------------------------------------------------------------------
    # Routers — OTA (existing)
    # -------------------------------------------------------------------------
    app.include_router(health_router)
    app.include_router(smart_switch_router)
    app.include_router(firmware_router)
    app.include_router(admin_router)

    # -------------------------------------------------------------------------
    # Routers — Smart Home (new)
    # -------------------------------------------------------------------------
    app.include_router(oauth_router)
    app.include_router(smart_home_router)
    app.include_router(smarthome_admin_router)
    app.include_router(consumer_router)
    app.include_router(admin_roles_router)
    app.include_router(device_models_router)

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
