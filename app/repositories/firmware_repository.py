import hashlib
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket
from pymongo import DESCENDING


class FirmwareRepository:
    def __init__(self, db: AsyncIOMotorDatabase, gridfs: AsyncIOMotorGridFSBucket, bucket_name: str) -> None:
        self.db = db
        self.gridfs = gridfs
        self.files_collection = db[f"{bucket_name}.files"]

    async def upload_binary(
        self,
        *,
        content: bytes,
        filename: str,
        mime: str,
        device_type: str,
        version: str,
    ) -> dict[str, Any]:
        sha256 = hashlib.sha256(content).hexdigest()
        now = datetime.now(UTC)
        metadata = {
            "device_type": device_type,
            "version": version,
            "sha256": sha256,
            "uploaded_at": now,
            "filename": filename,
            "size": len(content),
            "mime": mime,
        }

        file_id = await self.gridfs.upload_from_stream(filename, content, metadata=metadata)
        return {
            "file_id": str(file_id),
            "sha256": sha256,
            "size": len(content),
            "mime": mime,
            "filename": filename,
            "uploaded_at": now,
        }

    async def get_grid_out(self, file_id: str):
        return await self.gridfs.open_download_stream(ObjectId(file_id))

    async def find_latest_metadata(self, *, device_type: str, version: str) -> dict[str, Any] | None:
        return await self.files_collection.find_one(
            {"metadata.device_type": device_type, "metadata.version": version},
            sort=[("uploadDate", DESCENDING)],
        )
