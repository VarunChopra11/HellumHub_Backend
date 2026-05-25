from pymongo import ASCENDING, DESCENDING
from pymongo.errors import OperationFailure

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase, bucket_name: str) -> None:
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

    # GridFS files/chunks indexes are typically auto-managed, but this keeps metadata lookups fast.
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
        # Already exists with same/default options in many setups.
        pass
