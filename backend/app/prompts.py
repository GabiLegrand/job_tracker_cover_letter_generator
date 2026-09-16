import json
from typing import Any


SYSTEM_PROMPT = """You are a cover-letter writing assistant.

You will receive:
  1. A candidate's CV as JSON.
  2. A target company name.
  3. A job description.
  4. (Optionally) a user-provided job title.

Your job: produce a tailored cover letter in first person.

Hard rules:
- Use ONLY facts present in the CV. Never invent skills, employers, dates,
  degrees, projects, or numbers.
- If the CV does not contain something the job asks for, do not pretend;
  omit it or briefly acknowledge the gap honestly.
- Length: 350–450 words.
- Tone: confident, specific, grounded. Avoid generic claims like
  "I am a hard worker" without an accompanying concrete achievement.
- Structure: greeting, 2–3 short paragraphs linking selected highlights
  to the job ad, sign-off.
- Do NOT address the letter to a specific named person unless the job ad
  itself names one; otherwise use "Dear Hiring Team,".
- Do NOT use the emdash (—)

Output:
- Strict JSON with two keys:
    "job_title":   string
    "letter_content": string
- "job_title": if the user provided one, return it verbatim. Otherwise
  infer the most likely title from the job description.
- "letter_content": only the body of the letter. No JSON, no markdown
  fences, no commentary, no surrounding tags.
"""


def build_user_prompt(
    *,
    company_name: str,
    job_description: str,
    job_title: str | None,
    cv: dict[str, Any],
) -> str:
    cv_json = json.dumps(cv, indent=2, ensure_ascii=False)
    title_instruction = (
        f"User-provided job title: {job_title!r}. Use this VERBATIM in job_title."
        if job_title
        else "No job title was provided. Infer the most likely job title "
             "from the job description and use it in job_title."
    )
    return f"""Target company: {company_name}

{title_instruction}

Job description (verbatim):
---
{job_description}
---

Candidate CV (JSON):
---
{cv_json}
---

Selection guidance: from each role in the CV, pick the 3–6 highlights
whose `tags` / `skills_used` best match the job description. Emphasize
those in the letter and skip irrelevant roles.

Respond with strict JSON in exactly this shape:
{{
  "job_title": "...",
  "letter_content": "..."
}}
"""
