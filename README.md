# Cover Letter Generator

Self-hosted personal tool: paste a job description, get a tailored cover
letter drafted from your CV via OpenRouter.

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + Postgres + Alembic + WeasyPrint
- **Frontend**: React (Vite) + Tailwind, served by nginx
- **LLM**: OpenRouter API (model configurable via env var)

## Quick start

```bash
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# Drop your CV into backend/data/cv_database.json (schema below).
# A placeholder is provided.

docker compose up --build
```

Then open <http://localhost:5173>.

- API docs: <http://localhost:8000/docs>
- Postgres: `localhost:5432` (`coverletter` / `coverletter` / `coverletter`)

## CV database schema

`backend/data/cv_database.json` is loaded into memory at backend startup.
After editing it, restart the backend: `docker compose restart backend`.

```json
{
  "personal_info": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "+1 ...",
    "links": [{"label": "linkedin", "url": "https://..."}]
  },
  "experience": [
    {
      "company": "Acme",
      "title": "Senior Engineer",
      "start": "2021-01",
      "end": "present",
      "tags": ["python", "distributed-systems"],
      "skills_used": ["python", "kubernetes"],
      "highlights": ["Reduced API p99 by 40% by ..."]
    }
  ],
  "education": [],
  "skills": [],
  "tag_glossary": {}
}
```

The model selects 3–6 highlights per role whose `tags` / `skills_used`
best match the job ad.

## API surface (base `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| `GET`    | `/status`                      | Lock state |
| `GET`    | `/cover-letters`               | List (summary) |
| `POST`   | `/cover-letters`               | Create + generate (blocks for LLM) |
| `GET`    | `/cover-letters/{id}`          | Full record |
| `PUT`    | `/cover-letters/{id}`          | Manual edit |
| `POST`   | `/cover-letters/{id}/regenerate` | Re-run generation |
| `GET`    | `/cover-letters/{id}/pdf`      | Download PDF |
| `DELETE` | `/cover-letters/{id}`          | Delete row |

Only one generation runs at a time — concurrent calls get `409 Conflict`.

## Notes

- Frontend at `http://localhost:5173` (nginx → backend on `:8000`).
- Crash recovery: on backend startup, any rows stuck in `generating` are
  reset to `failed` with a note.
- To change model: edit `OPENROUTER_MODEL` in `.env`, then `docker compose restart backend`.
