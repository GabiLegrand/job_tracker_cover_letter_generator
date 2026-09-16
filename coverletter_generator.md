# Cover Letter Generator — Implementation Spec

## 1. Overview

A self-hosted system that generates tailored cover letters from a job description, using a static personal CV database (`cv_database.json`) as source material. Consists of:

- **Backend**: containerized API (Python/FastAPI) + Postgres DB
- **Frontend**: containerized SPA (React) — list, create, view/edit, download, delete cover letters
- **Generation engine**: LLM call (Defined model, via OpenRouter API) that selects relevant CV content and drafts the letter

No queueing, no multi-user auth, no multi-tenancy — this is a personal tool, single job in flight at a time.

---

## 2. Architecture

```
                    ┌─────────────────────┐
                    │   Frontend (SPA)     │
                    │   React + Vite       │
                    │   served via nginx   │
                    └──────────┬───────────┘
                               │ HTTP (REST/JSON)
                               ▼
                    ┌─────────────────────┐
                    │   Backend API        │
                    │   FastAPI (Python)   │
                    │                       │
                    │  - in-memory lock     │
                    │  - cv_database.json   │
                    │    loaded on startup  │
                    │  - LLM client (Rest request or OpenAi lib)        │
                    │  - PDF renderer       │
                    └──────────┬───────────┘
                               │ SQL (asyncpg/SQLAlchemy)
                               ▼
                    ┌─────────────────────┐
                    │   Postgres DB         │
                    │   cover_letters table │
                    └─────────────────────┘
```

Three containers via `docker-compose`: `backend`, `frontend`, `db`. `cv_database.json` is mounted read-only into the backend container (bind mount or baked into the image) and parsed once into memory on startup — not stored in Postgres, per your instruction.

---

## 3. Data Model

### 3.1 Postgres — `cover_letters` table

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` (PK, default `gen_random_uuid()`) | |
| `company_name` | `TEXT NOT NULL` | |
| `job_title` | `TEXT NOT NULL` | Provided by user, or extracted from the job description by the LLM if omitted |
| `job_description` | `TEXT NOT NULL` | Raw pasted job ad |
| `letter_content` | `TEXT` | Current letter text (nullable while generating) |
| `status` | `TEXT NOT NULL DEFAULT 'pending'` | `pending` \| `generating` \| `ready` \| `failed` |
| `error_message` | `TEXT` | Populated if `status = failed` |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | Bumped on regenerate/edit |

Index on `(company_name, job_title)` for the list view. No auth/user table — single-user tool.

### 3.2 CV database (`cv_database.json`)

Already defined (see previous deliverable). Loaded once at backend startup into an in-memory Python object; reload requires a container restart (acceptable for a personal tool, but see §9 open questions).

---

## 4. Generation Pipeline

1. Client submits `company_name` (required), `job_description` (required), `job_title` (optional).
2. Backend checks the **global lock** (§6). If locked → `409 Conflict`, request rejected immediately (no queueing).
3. Lock acquired. Row inserted with `status = generating`.
4. Backend builds a prompt combining:
   - The job description (verbatim)
   - The full CV database (or a pre-filtered subset — see below)
   - Instructions: extract/confirm job title if not supplied, select the most relevant 3–6 highlights per role by matching `tags`/`skills_used` against the job description, write a letter in first person, keep it to ~350–450 words, no invented facts.
5. Call to OpenRouter API (model configurable via env var, e.g. `minimax/minimax-m3`... see note in §9).
6. Response parsed: `letter_content` and (if not user-provided) extracted `job_title`.
7. Row updated: `status = ready`, `letter_content`, `job_title`, `updated_at`.
8. Lock released.
9. On any failure (API error, timeout): `status = failed`, `error_message` set, lock released.

**Regeneration** (`POST /cover-letters/{id}/regenerate`) re-runs steps 2–9 against the same stored `job_description`/`company_name`, overwriting `letter_content`. Same lock applies.

**Filtering strategy for step 4**: for v1, simplest approach is to pass the entire `cv_database.json` in the prompt (it's small enough token-wise) and let the model do the selection itself, guided by the `tags` field. A pre-filter (keyword match job description against `tag_glossary`) is a nice-to-have optimization, not required for v1.

---

## 5. Concurrency / Lock Mechanism

- A single in-memory flag (e.g. `generation_lock: bool`, guarded by `asyncio.Lock`) on the backend process.
- Set to `True` for the duration of generation (create or regenerate).
- Any incoming create/regenerate request while locked → `409 Conflict` with a clear error body (e.g. `{"error": "generation_in_progress", "cover_letter_id": "..."}`).
- `GET /status` endpoint exposes current lock state (and which letter is generating, if any) so the frontend can disable the "new letter" form proactively rather than relying only on the 409.
- **Caveat**: this only works correctly with a single backend process/replica (no horizontal scaling). Fine for this tool; noted as a constraint, not a bug.
- If the container restarts mid-generation, the lock is lost and the row is left stuck in `status = generating`. v1 accepts this; a future improvement could add a startup check that resets any `generating` rows to `failed`.

---

## 6. API Specification

Base path: `/api/v1`

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/status` | Returns lock state: `{"locked": bool, "cover_letter_id": str \| null}` |
| `GET` | `/cover-letters` | List all letters — returns `id`, `company_name`, `job_title`, `status`, `created_at`, `updated_at` (no full text/description, keeps list light) |
| `POST` | `/cover-letters` | Create + generate a new letter. Body: `{"company_name": str, "job_description": str, "job_title": str \| null}`. Returns the created row (likely `status: generating` immediately, `ready` once the (synchronous) call completes — see note below) |
| `GET` | `/cover-letters/{id}` | Full record as raw JSON/text: company, job title, job description, letter content, status |
| `PUT` | `/cover-letters/{id}` | Manual edit. Body: any of `company_name`, `job_title`, `job_description`, `letter_content`. Updates `updated_at`. Does **not** trigger regeneration. |
| `POST` | `/cover-letters/{id}/regenerate` | Re-run generation against current stored `job_description`/`company_name`. Subject to the same lock. |
| `GET` | `/cover-letters/{id}/pdf` | Renders `letter_content` to PDF on the fly and returns it as a file download (`application/pdf`) — not stored in DB, generated per request |
| `DELETE` | `/cover-letters/{id}` | Deletes the row |

**On synchronous vs. async generation**: `POST /cover-letters` will block the HTTP request for the duration of the LLM call (typically a few seconds to ~30s). Given "no queue, one job at a time" this is the simplest correct model — the frontend just shows a loading state for that request. No websockets/polling needed for v1. (If generation ever gets slow/flaky, this is the first thing to revisit — see §9.)

---

## 7. PDF Generation

- Rendered on-demand from `letter_content` at request time (not stored as a blob), so edits are always reflected in the download.
- Library candidate: **WeasyPrint** (HTML/CSS → PDF, easy to style, good text layout) or **ReportLab** (more manual, more control). Recommendation: WeasyPrint — wrap `letter_content` in a simple HTML template (name/contact header optional, clean serif font, margins) and render.
- Filename convention: `cover-letter_{company_name}_{job_title}.pdf` (slugified).

---

## 8. Frontend

SPA with three views:

### 8.1 Layout
- **Left sidebar** (persistent): list of existing letters, each row showing `company_name` + `job_title` (+ status badge if `generating`/`failed`). Per-row actions: **Download** (calls PDF endpoint), **Delete** (opens confirmation modal → `DELETE` on confirm). Clicking a row opens the edit view.
- A persistent **"+ New"** button/link at the top of the sidebar → navigates to the create page. Disabled (with tooltip "generation in progress") when `GET /status` reports locked.

### 8.2 Create page (`/new`)
- Form: `company_name` (required), `job_title` (optional), `job_description` (required, textarea).
- On submit: `POST /cover-letters`. Show a loading state for the duration of the request (this is the "one job, no queue" constraint — submit button disabled while in flight, and disabled globally if `/status` shows locked when the page loads).
- On success: redirect to the new letter's edit page.
- On `409`: show inline message that a generation is already in progress.

### 8.3 Edit page (`/letters/:id`)
- Editable fields: `company_name`, `job_title`, `job_description` (collapsible/secondary), `letter_content` (primary, large textarea).
- **Save** button → `PUT /cover-letters/{id}` (manual edits only, no regeneration).
- **Regenerate** button → `POST /cover-letters/{id}/regenerate`, disabled while locked, shows loading state, refreshes `letter_content` on completion.
- **Download PDF** button → `GET /cover-letters/{id}/pdf`.
- **Delete** button → same confirmation modal as sidebar.

No routing/auth complexity beyond these three views.

---

## 9. Assumptions & Open Questions

Please confirm or adjust before implementation starts:

1. **LLM provider/model**: OpenRouter API via `OPENROUTER_API_KEY` env var — confirm you want to bring your own key . Model name should be pinned via env var so it's easy to bump later.
2. **Synchronous generation**: confirmed simplest for "one job, no queue" — acceptable that the create/regenerate HTTP call blocks for the duration of the LLM call?
3. **CV database reload**: v1 = restart container to pick up an updated `cv_database.json`. Acceptable, or do you want a `POST /admin/reload-cv` endpoint?
4. **PDF styling**: plain letter format is fine, or do you want your name/contact header (from `personal_info` in the CV JSON) automatically included at the top of the PDF?
5. **Crash recovery**: rows stuck in `generating` after a crash — leave as manual cleanup for v1, or add auto-reset-to-`failed` on backend startup?
6. **Frontend styling**: any preference (Tailwind, plain CSS, component library) or should I just make it clean/functional?

---

## 10. Proposed Project Structure

```
cover-letter-generator/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # FastAPI app, routes
│   │   ├── db.py                 # SQLAlchemy engine/session
│   │   ├── models.py             # ORM model for cover_letters
│   │   ├── schemas.py            # Pydantic request/response models
│   │   ├── generation.py         # Prompt building + OpenRouter call
│   │   ├── pdf.py                 # WeasyPrint rendering
│   │   ├── lock.py                # In-memory generation lock
│   │   └── cv_data.py             # Loads/parses cv_database.json on startup
│   └── data/
│       └── cv_database.json      # mounted/copied in
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── pages/
│       │   ├── NewLetter.jsx
│       │   └── EditLetter.jsx
│       ├── components/
│       │   ├── Sidebar.jsx
│       │   └── DeleteConfirmModal.jsx
│       └── api.js                 # fetch wrappers
└── README.md
```

---

## Next Step

Once you confirm/adjust the open questions in §9, I'll scaffold the full project: `docker-compose.yml`, backend (FastAPI + SQLAlchemy + Alembic migration for the table, generation + PDF logic), and the React frontend.