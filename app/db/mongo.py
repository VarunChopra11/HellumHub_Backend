import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorGridFSBucket

from app.core.config import Settings

logger = logging.getLogger(__name__)


class MongoState:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None
        self.gridfs: AsyncIOMotorGridFSBucket | None = None

    async def connect(self, settings: Settings) -> None:
        self.client = AsyncIOMotorClient(
            settings.mongo_uri,
            appname=settings.app_name,
            minPoolSize=settings.mongo_min_pool_size,
            maxPoolSize=settings.mongo_max_pool_size,
            serverSelectionTimeoutMS=settings.mongo_server_selection_timeout_ms,
            connectTimeoutMS=settings.mongo_connect_timeout_ms,
            socketTimeoutMS=settings.mongo_socket_timeout_ms,
            retryWrites=True,
            uuidRepresentation="standard",
        )

        await self.client.admin.command("ping")
        self.db = self.client[settings.mongo_db_name]
        self.gridfs = AsyncIOMotorGridFSBucket(self.db, bucket_name=settings.gridfs_bucket_name)
        logger.info("connected_to_mongo db=%s", settings.mongo_db_name)

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()
            logger.info("mongo_connection_closed")


mongo_state = MongoState()
