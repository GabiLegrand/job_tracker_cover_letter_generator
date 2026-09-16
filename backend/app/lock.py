import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import HTTPException

log = logging.getLogger("lock")


class GenerationLock:
    """A single global generation lock for the whole backend process.

    Implemented as an asyncio.Lock + a `current_id` slot. Holding the lock
    also populates `current_id` so /status can report which letter is
    currently being generated.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._current_id: UUID | None = None

    @property
    def locked(self) -> bool:
        return self._lock.locked()

    @property
    def current_id(self) -> UUID | None:
        return self._current_id

    @asynccontextmanager
    async def acquire(self, letter_id: UUID) -> AsyncIterator[None]:
        if self._lock.locked():
            log.info(
                "lock_conflict requested_by=%s held_by=%s",
                letter_id, self._current_id,
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "generation_in_progress",
                    "cover_letter_id": str(self._current_id),
                },
            )
        await self._lock.acquire()
        self._current_id = letter_id
        log.info("lock_acquired letter_id=%s", letter_id)
        try:
            yield
        finally:
            self._current_id = None
            self._lock.release()
            log.info("lock_released letter_id=%s", letter_id)


lock = GenerationLock()
