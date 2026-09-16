import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


def load_cv_database() -> dict:
    path = Path(settings.cv_path)
    if not path.exists():
        raise FileNotFoundError(f"cv_database.json not found at {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("cv_database.json must be a JSON object at the top level")
    if "personal_info" not in data:
        raise ValueError("cv_database.json must contain a 'personal_info' key")
    return data


# Loaded once at backend import time (i.e. container start).
# Restart the backend container to pick up edits to the file.
CV: dict = load_cv_database()
logger.info(
    "Loaded CV for %s with %d role(s)",
    CV.get("personal_info", {}).get("name", "<unnamed>"),
    len(CV.get("experience", [])),
)
