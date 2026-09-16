from fastapi import APIRouter

from app.lock import lock
from app.schemas import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    return StatusResponse(locked=lock.locked, cover_letter_id=lock.current_id)
