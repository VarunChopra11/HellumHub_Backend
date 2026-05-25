from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz(db=Depends(get_db)) -> HealthResponse:
    await db.command("ping")
    return HealthResponse(status="ok", now=datetime.now(UTC))
