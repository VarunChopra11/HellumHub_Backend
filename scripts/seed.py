import asyncio
import hashlib
from datetime import UTC, datetime

from app.db.indexes import ensure_indexes
from app.db.mongo import mongo_state
from app.core.config import get_settings


async def seed() -> None:
    settings = get_settings()
    await mongo_state.connect(settings)
    assert mongo_state.db is not None
    assert mongo_state.gridfs is not None

    await ensure_indexes(mongo_state.db, settings.gridfs_bucket_name)

    mac = "AA:BB:CC:DD:EE:FF"
    await mongo_state.db.devices.update_one(
        {"mac": mac},
        {
            "$set": {
                "mac": mac,
                "device_type": "smart_switch",
                "current_version": "1.0.0",
                "last_seen_at": datetime.now(UTC),
                "last_ip": "127.0.0.1",
                "last_check_result": "seed",
                "rollout_group": None,
                "blocked": False,
                "updated_at": datetime.now(UTC),
            },
            "$setOnInsert": {"created_at": datetime.now(UTC)},
        },
        upsert=True,
    )

    bin_content = b"ESP32-FIRMWARE-SEED-BINARY"
    checksum = hashlib.sha256(bin_content).hexdigest()
    file_id = await mongo_state.gridfs.upload_from_stream(
        "smart_switch_1.1.0.bin",
        bin_content,
        metadata={
            "device_type": "smart_switch",
            "version": "1.1.0",
            "sha256": checksum,
            "uploaded_at": datetime.now(UTC),
            "filename": "smart_switch_1.1.0.bin",
            "size": len(bin_content),
            "mime": "application/octet-stream",
        },
    )

    await mongo_state.db.releases.update_one(
        {"device_type": "smart_switch", "version": "1.1.0"},
        {
            "$set": {
                "device_type": "smart_switch",
                "version": "1.1.0",
                "rollout_percentage": 100,
                "enabled": True,
                "notes": "seed release",
                "firmware_file_id": str(file_id),
                "sha256": checksum,
                "size": len(bin_content),
                "mime": "application/octet-stream",
                "filename": "smart_switch_1.1.0.bin",
                "updated_at": datetime.now(UTC),
            },
            "$setOnInsert": {"created_at": datetime.now(UTC)},
        },
        upsert=True,
    )

    print("Seeded: 1 device + 1 release + 1 GridFS firmware object")
    await mongo_state.close()


if __name__ == "__main__":
    asyncio.run(seed())
