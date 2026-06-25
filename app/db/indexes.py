from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase, bucket_name: str) -> None:
    # -------------------------------------------------------------------------
    # OTA — existing indexes (unchanged)
    # -------------------------------------------------------------------------
    await db.devices.create_index([("mac", ASCENDING)], unique=True, name="uq_mac")
    await db.releases.create_index(
        [("device_type", ASCENDING), ("version", ASCENDING)],
        unique=True,
        name="uq_device_type_version",
    )
    await db.releases.create_index(
        [("device_type", ASCENDING), ("enabled", ASCENDING)],
        name="idx_release_active_lookup",
    )
    await db.audit_checks.create_index(
        [("device_type", ASCENDING), ("mac", ASCENDING), ("checked_at", DESCENDING)],
        name="idx_device_mac_checked_at_desc",
    )
    await db.device_overrides.create_index(
        [("device_type", ASCENDING), ("mac", ASCENDING)],
        unique=True,
        name="uq_override_device_mac",
    )
    await db.device_overrides.create_index(
        [("device_type", ASCENDING), ("version", ASCENDING)],
        name="idx_override_lookup",
    )

    files_collection = db[f"{bucket_name}.files"]
    chunks_collection = db[f"{bucket_name}.chunks"]
    await files_collection.create_index(
        [("metadata.device_type", ASCENDING), ("metadata.version", ASCENDING)],
        name="idx_fw_meta_device_version",
    )
    try:
        await chunks_collection.create_index(
            [("files_id", ASCENDING), ("n", ASCENDING)],
            unique=True,
            name="files_id_1_n_1",
        )
    except OperationFailure:
        pass

    # -------------------------------------------------------------------------
    # Consumer users — Google SSO
    # -------------------------------------------------------------------------
    await db.users.create_index(
        [("google_sub", ASCENDING)],
        unique=True,
        name="uq_user_google_sub",
    )
    await db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        sparse=True,
        name="uq_user_email",
    )

    # -------------------------------------------------------------------------
    # Smart Home devices
    # -------------------------------------------------------------------------
    await db.smarthome_devices.create_index(
        [("mac", ASCENDING)],
        unique=True,
        name="uq_smarthome_device_mac",
    )
    await db.smarthome_devices.create_index(
        [("user_id", ASCENDING)],
        name="idx_smarthome_device_user_id",
    )
    # Compound index for endpoint state lookups (positional operator queries)
    await db.smarthome_devices.create_index(
        [("mac", ASCENDING), ("endpoints.id", ASCENDING)],
        name="idx_smarthome_device_mac_endpoint",
    )

    # -------------------------------------------------------------------------
    # Device Model catalog
    # -------------------------------------------------------------------------
    await db.device_models.create_index(
        [("model_id", ASCENDING)],
        unique=True,
        name="uq_device_model_id",
    )

    # -------------------------------------------------------------------------
    # Admin RBAC
    # -------------------------------------------------------------------------
    await db.admin_users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="uq_admin_user_email",
    )

    # -------------------------------------------------------------------------
    # OAuth 2.0 authorization codes — TTL auto-expiry
    # -------------------------------------------------------------------------
    await db.oauth_codes.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_oauth_code_expiry",
    )
    await db.oauth_codes.create_index(
        [("code", ASCENDING)],
        unique=True,
        name="uq_oauth_code",
    )

    # -------------------------------------------------------------------------
    # Refresh tokens — TTL auto-expiry
    # -------------------------------------------------------------------------
    await db.refresh_tokens.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_refresh_token_expiry",
    )
    await db.refresh_tokens.create_index(
        [("token", ASCENDING)],
        unique=True,
        name="uq_refresh_token",
    )

    # -------------------------------------------------------------------------
    # MQTT Binding Tokens — TTL auto-expiry
    # -------------------------------------------------------------------------
    await db.binding_tokens.create_index(
        [("expires_at", ASCENDING)],
        expireAfterSeconds=0,
        name="ttl_binding_token_expiry",
    )
    await db.binding_tokens.create_index(
        [("token", ASCENDING)],
        unique=True,
        name="uq_binding_token",
    )
