import json
import logging
import re
import time
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI

from app.config import settings
from app.prompts import SYSTEM_PROMPT, build_user_prompt

log = logging.getLogger("generation")

# Match a markdown code fence with optional language tag (e.g. ```json or ```).
# Captures the body inside the fence. The DOTALL flag lets `.` span newlines.
_FENCED_JSON_RE = re.compile(
    r"```(?:json|JSON)?\s*\n?(.*?)\n?```",
    re.DOTALL,
)
# Match the first balanced-looking JSON object/array in arbitrary text.
# Used as a last resort when the model wraps output in prose without fences.
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


def _extract_json(raw: str) -> Any:
    """Parse `raw` as JSON, tolerating common model-output quirks.

    Strategy (first success wins):
      1. Direct ``json.loads`` -- happy path.
      2. Strip a markdown code fence (``\\`\\`\\`json ... \\`\\`\\``` or just
         ``\\`\\`\\`` ... ``\\`\\`\\```) and retry.
      3. Greedily grab the first ``{...}`` or ``[...]`` substring and retry.

    Raises ``ValueError`` if none of the attempts succeed. The original
    ``JSONDecodeError`` from step 3 is chained for debugging.
    """
    # 1. Already-valid JSON
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Markdown-wrapped JSON
    fence_match = _FENCED_JSON_RE.search(raw)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. Bare JSON embedded in prose -- prefer object (our schema is an object)
    last_exc: json.JSONDecodeError | None = None
    for pattern in (_JSON_OBJECT_RE, _JSON_ARRAY_RE):
        block_match = pattern.search(raw)
        if not block_match:
            continue
        try:
            return json.loads(block_match.group(0))
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue

    raise ValueError(
        f"Could not extract JSON from model output: {raw[:200]!r}"
    ) from last_exc


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": settings.app_url,
            "X-Title": settings.app_title,
        },
        timeout=60.0,
    )

def sanitize_job_title(text):
    text_no_par = re.sub(r"\s*(?:\(.*|,.*)$", "", text)
    text_no_comma = text_no_par.split(",")[0]
    return text_no_comma

async def generate_cover_letter(
    *,
    letter_id: UUID,
    company_name: str,
    job_description: str,
    job_title: str | None,
    cv: dict,
) -> tuple[str, str]:
    """Call OpenRouter, return (extracted_or_passthrough_title, letter_text).

    All progress is logged under the `generation` logger, keyed by `letter_id`
    so you can `grep letter_id=<uuid>` to see a full trace for one request.
    """
    log.info(
        "input letter_id=%s company=%r job_title=%r "
        "job_desc_chars=%d cv_chars=%d",
        letter_id, company_name, job_title,
        len(job_description), len(json.dumps(cv, ensure_ascii=False)),
    )

    client = _get_client()
    user_prompt = build_user_prompt(
        company_name=company_name,
        job_description=job_description,
        job_title=sanitize_job_title(job_title),
        cv=cv,
    )
    log.info(
        "prompt_built letter_id=%s system_chars=%d user_chars=%d",
        letter_id, len(SYSTEM_PROMPT), len(user_prompt),
    )
    # Full prompt bodies are usually noise — only dump them when debugging.
    log.debug("prompt_dump letter_id=%s system=%r", letter_id, SYSTEM_PROMPT)
    log.debug("prompt_dump letter_id=%s user=%r",   letter_id, user_prompt)

    log.info(
        "openrouter_request_start letter_id=%s model=%s temperature=%.2f "
        "max_tokens=%d",
        letter_id, settings.openrouter_model, 0.4, 1200,
    )
    t0 = time.monotonic()
    try:
        resp = await client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        elapsed_ms = (time.monotonic() - t0) * 1000
        log.exception(
            "openrouter_request_failed letter_id=%s elapsed_ms=%.0f",
            letter_id, elapsed_ms,
        )
        raise
    log.info(f"Response : {resp}")
    elapsed_ms = (time.monotonic() - t0) * 1000
    usage = getattr(resp, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None
    finish_reason = (
        resp.choices[0].finish_reason if resp.choices else None
    )
    log.info(
        "openrouter_request_done letter_id=%s elapsed_ms=%.0f "
        "finish_reason=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s",
        letter_id, elapsed_ms, finish_reason,
        prompt_tokens, completion_tokens, total_tokens,
    )

    raw_content = resp.choices[0].message.content if resp.choices else ""
    raw = (raw_content or "").strip()
    log.info(
        "openrouter_response_text letter_id=%s chars=%d preview=%r",
        letter_id, len(raw), raw[:200].replace("\n", "\\n"),
    )

    if not raw:
        raise ValueError("OpenRouter returned empty content")

    try:
        parsed = _extract_json(raw)
    except ValueError as exc:
        log.error(
            "openrouter_response_invalid_json letter_id=%s err=%s body=%r",
            letter_id, exc, raw[:500],
        )
        raise

    extracted_title = (parsed.get("job_title") or "").strip() or (job_title or "").strip()
    letter = (parsed.get("letter_content") or "").strip()
    if not letter:
        log.error("openrouter_response_empty_letter letter_id=%s", letter_id)
        raise ValueError("Model returned empty letter_content")
    if not extracted_title:
        extracted_title = "Unknown role"

    log.info(
        "parsed letter_id=%s title=%r letter_chars=%d",
        letter_id, extracted_title, len(letter),
    )
    return extracted_title, letter
