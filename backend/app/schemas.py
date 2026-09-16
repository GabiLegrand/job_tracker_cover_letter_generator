from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["pending", "generating", "ready", "failed"]


class CoverLetterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    job_title: str
    job_ad_url: str | None = None
    status: Status
    created_at: datetime
    updated_at: datetime


class CoverLetterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    job_title: str
    job_description: str
    job_ad_url: str | None = None
    letter_content: str | None
    status: Status
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class CoverLetterCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    job_description: str = Field(..., min_length=1)
    job_ad_url: str | None = Field(default=None, max_length=2000)


class CoverLetterUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    job_description: str | None = Field(default=None, min_length=1)
    letter_content: str | None = None
    job_ad_url: str | None = Field(default=None, max_length=2000)


class StatusResponse(BaseModel):
    locked: bool
    cover_letter_id: UUID | None = None

class LinkedInAdRegister(BaseModel):
    url: str = Field(..., min_length=1)
    html_content: str = Field(..., min_length=1)

class LinkedInAdResponse(BaseModel):
    registered_ad_id: UUID | None = None


class CoverLetterBatchGetRequest(BaseModel):
    ids: list[UUID] = Field(..., min_length=1, max_length=100)


class CoverLetterBatchGetResponse(BaseModel):
    found: list[CoverLetterDetail]
    missing: list[UUID]
