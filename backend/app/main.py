import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import update

from app.config import settings
from app.cv_data import CV
from app.db import SessionLocal
from app.models import CoverLetter
from app.routes import cover_letters as cl_routes
from app.routes import pdf as pdf_routes
from app.routes import status as status_routes
from app.routes import linkedin

http_log = logging.getLogger("http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("startup").info(
        "startup cv_loaded name=%r roles=%d skills=%d",
        CV.get("personal_info", {}).get("name", "<unnamed>"),
        len(CV.get("experience", [])),
        sum(len(v) if isinstance(v, list) else 0
            for v in (CV.get("skills") or {}).values() if isinstance(v, list)),
    )

    async with SessionLocal() as session:
        result = await session.execute(
            update(CoverLetter)
            .where(CoverLetter.status == "generating")
            .values(
                status="failed",
                error_message="backend restarted during generation",
            )
        )
        await session.commit()
        if result.rowcount:
            logging.getLogger("startup").warning(
                "startup reset stuck_rows count=%d", result.rowcount
            )

    yield

    logging.getLogger("shutdown").info("shutdown complete")


app = FastAPI(title=settings.app_title, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        settings.app_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw = await request.body()
    try:
        body_text = raw.decode("utf-8", errors="replace")[:2000]
    except Exception:
        body_text = repr(raw)[:2000]
    http_log.warning(
        "request_validation_failed method=%s path=%s body=%r errors=%s",
        request.method, request.url.path, body_text, exc.errors(),
    )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    http_log.info(
        "request_start method=%s path=%s query=%r",
        request.method,
        request.url.path,
        request.url.query or "",
    )
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.monotonic() - t0) * 1000
        http_log.exception(
            "request_failed method=%s path=%s elapsed_ms=%.0f",
            request.method, request.url.path, elapsed_ms,
        )
        raise
    elapsed_ms = (time.monotonic() - t0) * 1000
    http_log.info(
        "request_done method=%s path=%s status=%s elapsed_ms=%.0f",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


API_PREFIX = "/api/v1"
app.include_router(status_routes.router, prefix=API_PREFIX)
app.include_router(cl_routes.router, prefix=API_PREFIX)
app.include_router(pdf_routes.router, prefix=API_PREFIX)
app.include_router(linkedin.router, prefix=API_PREFIX)

@app.get("/health")
async def health():
    return {"status": "ok"}
