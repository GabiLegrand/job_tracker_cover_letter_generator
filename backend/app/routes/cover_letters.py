import logging
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import SessionLocal


import asyncio
import time
from uuid import UUID, uuid4

# Keep references to in-flight background tasks so they aren't GC'd
_background_tasks: set[asyncio.Task] = set()



from app.cv_data import CV
from app.db import get_session
from app.generation import generate_cover_letter
from app.lock import lock
from app.models import CoverLetter
from app.schemas import (
    CoverLetterBatchGetRequest,
    CoverLetterBatchGetResponse,
    CoverLetterCreate,
    CoverLetterDetail,
    CoverLetterSummary,
    CoverLetterUpdate,
)

log = logging.getLogger("route")

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


@router.get("", response_model=list[CoverLetterSummary])
async def list_cover_letters(session: AsyncSession = Depends(get_session)):
    log.info("list_cover_letters")
    result = await session.execute(
        select(CoverLetter).order_by(CoverLetter.updated_at.desc())
    )
    rows = result.scalars().all()
    log.info("list_cover_letters returned=%d", len(rows))
    return rows

@router.post("", response_model=CoverLetterDetail, status_code=201)
async def create_cover_letter(
    payload: CoverLetterCreate,
    session: AsyncSession = Depends(get_session),
):
    new_id = uuid4()
    t0 = time.monotonic()
    log.info(
        "create_request letter_id=%s company=%r job_title=%r job_desc_chars=%d",
        new_id, payload.company_name, payload.job_title, len(payload.job_description),
    )

    letter = CoverLetter(
        id=new_id,
        company_name=payload.company_name,
        job_title=payload.job_title or "Pending…",
        job_description=payload.job_description,
        job_ad_url=payload.job_ad_url,
        letter_content=None,
        status="generating",
    )
    session.add(letter)
    await session.commit()
    await session.refresh(letter)
    log.info(
        "create_row_inserted letter_id=%s status=generating job_ad_url=%r",
        new_id, payload.job_ad_url,
    )

    _spawn(_generate_and_store(
        new_id, payload.company_name, payload.job_description, payload.job_title, t0,
    ))

    return letter  # returned immediately, status="generating"

def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
async def _generate_and_store(
    letter_id: UUID,
    company_name: str,
    job_description: str,
    job_title: str | None,
    t0: float,
) -> None:
    """Runs fully detached from the request. Opens its own session."""
    async with SessionLocal() as session:
        async with lock.acquire(letter_id):
            letter = await session.get(CoverLetter, letter_id)
            if letter is None:
                log.error("generate_missing_row letter_id=%s", letter_id)
                return
            try:
                extracted_title, content = await generate_cover_letter(
                    letter_id=letter_id,
                    company_name=company_name,
                    job_description=job_description,
                    job_title=job_title,
                    cv=CV,
                )
                letter.job_title = extracted_title or job_title or "Unknown role"
                letter.letter_content = content
                letter.status = "ready"
                letter.error_message = None
                await session.commit()
                log.info(
                    "create_done letter_id=%s status=ready title=%r "
                    "letter_chars=%d total_elapsed_ms=%.0f",
                    letter_id, extracted_title, len(content),
                    (time.monotonic() - t0) * 1000,
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("create_failed letter_id=%s", letter_id)
                letter.status = "failed"
                letter.error_message = str(exc)[:500]
                await session.commit()
                log.warning(
                    "create_done letter_id=%s status=failed total_elapsed_ms=%.0f",
                    letter_id, (time.monotonic() - t0) * 1000,
                )

@router.post("/batch-get", response_model=CoverLetterBatchGetResponse)
async def batch_get_cover_letters(
    payload: CoverLetterBatchGetRequest,
    session: AsyncSession = Depends(get_session),
):
    requested = list(dict.fromkeys(payload.ids))  # de-dup, preserve order
    log.info("batch_get_cover_letters requested=%d", len(requested))
    result = await session.execute(
        select(CoverLetter).where(CoverLetter.id.in_(requested))
    )
    rows = result.scalars().all()
    found_ids = {row.id for row in rows}
    missing = [letter_id for letter_id in requested if letter_id not in found_ids]
    log.info(
        "batch_get_cover_letters returned found=%d missing=%d",
        len(rows), len(missing),
    )
    return CoverLetterBatchGetResponse(found=rows, missing=missing)


@router.get("/{letter_id}", response_model=CoverLetterDetail)
async def get_cover_letter(
    letter_id: UUID, session: AsyncSession = Depends(get_session)
):
    letter = await session.get(CoverLetter, letter_id)
    if letter is None:
        log.info("get_cover_letter letter_id=%s -> 404", letter_id)
        raise HTTPException(status_code=404, detail="Not found")
    log.info("get_cover_letter letter_id=%s status=%s", letter_id, letter.status)
    return letter


@router.put("/{letter_id}", response_model=CoverLetterDetail)
async def update_cover_letter(
    letter_id: UUID,
    payload: CoverLetterUpdate,
    session: AsyncSession = Depends(get_session),
):
    log.info("update_cover_letter letter_id=%s fields=%s", letter_id, list(payload.model_dump(exclude_unset=True).keys()))
    letter = await session.get(CoverLetter, letter_id)
    if letter is None:
        log.info("update_cover_letter letter_id=%s -> 404", letter_id)
        raise HTTPException(status_code=404, detail="Not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(letter, key, value)
    await session.commit()
    await session.refresh(letter)
    log.info("update_cover_letter letter_id=%s -> ok status=%s", letter_id, letter.status)
    return letter


@router.delete("/{letter_id}", status_code=204)
async def delete_cover_letter(
    letter_id: UUID, session: AsyncSession = Depends(get_session)
):
    letter = await session.get(CoverLetter, letter_id)
    if letter is None:
        log.info("delete_cover_letter letter_id=%s -> 404", letter_id)
        raise HTTPException(status_code=404, detail="Not found")
    await session.delete(letter)
    await session.commit()
    log.info("delete_cover_letter letter_id=%s -> ok", letter_id)
    return None


@router.post("/{letter_id}/regenerate", response_model=CoverLetterDetail)
async def regenerate_cover_letter(
    letter_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    t0 = time.monotonic()
    log.info("regenerate_request letter_id=%s", letter_id)
    letter = await session.get(CoverLetter, letter_id)
    if letter is None:
        log.info("regenerate_request letter_id=%s -> 404", letter_id)
        raise HTTPException(status_code=404, detail="Not found")

    async with lock.acquire(letter.id):
        letter.status = "generating"
        letter.error_message = None
        await session.commit()
        log.info("regenerate_row_marked letter_id=%s status=generating", letter_id)
        try:
            extracted_title, content = await generate_cover_letter(
                letter_id=letter.id,
                company_name=letter.company_name,
                job_description=letter.job_description,
                job_title=letter.job_title,
                cv=CV,
            )
            letter.job_title = extracted_title or letter.job_title
            letter.letter_content = content
            letter.status = "ready"
            await session.commit()
            log.info(
                "regenerate_done letter_id=%s status=ready "
                "title=%r letter_chars=%d total_elapsed_ms=%.0f",
                letter_id, extracted_title, len(content), (time.monotonic() - t0) * 1000,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("regenerate_failed letter_id=%s", letter_id)
            letter.status = "failed"
            letter.error_message = str(exc)[:500]
            await session.commit()
            log.warning(
                "regenerate_done letter_id=%s status=failed total_elapsed_ms=%.0f",
                letter_id, (time.monotonic() - t0) * 1000,
            )

    await session.refresh(letter)
    return letter
