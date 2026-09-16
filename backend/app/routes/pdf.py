from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import CoverLetter
from app.pdf import pdf_filename, render_pdf

router = APIRouter(prefix="/cover-letters", tags=["pdf"])


@router.get("/{letter_id}/pdf")
async def get_pdf(
    letter_id: UUID, session: AsyncSession = Depends(get_session)
):
    letter = await session.get(CoverLetter, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="Not found")
    if letter.status != "ready" or not letter.letter_content:
        raise HTTPException(
            status_code=409,
            detail=f"Letter not ready (status={letter.status})",
        )
    pdf_bytes, _ = render_pdf(letter.letter_content)
    filename = pdf_filename(letter.company_name, letter.job_title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
