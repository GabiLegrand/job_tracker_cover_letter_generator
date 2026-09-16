import logging
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import LinkedInAd
from app.schemas import (
    LinkedInAdRegister,
    LinkedInAdResponse
)

log = logging.getLogger("route")

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

@router.post("/register", response_model=LinkedInAdResponse)
async def register_linked_in_ad(
    payload: LinkedInAdRegister,
    session: AsyncSession = Depends(get_session)
):
    log.info("Received new linkedin add to register")
    new_id = uuid4()
    ad = LinkedInAd(
        id=new_id,
        url=payload.url,
        html_content=payload.html_content,
    )
    session.add(ad)
    await session.commit()
    await session.refresh(ad)

    log.info(f"Successfully registered linkedin ad: {ad.id}")

    return LinkedInAdResponse(registered_ad_id=ad.id)