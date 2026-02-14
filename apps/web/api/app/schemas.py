from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Selection(BaseModel):
    mode: Literal["all", "indices", "regions_sectors"] = "all"
    regions: list[int] = Field(default_factory=list)
    sectors: list[int] = Field(default_factory=list)
    indices: list[int] = Field(default_factory=list)


class Analysis(BaseModel):
    type: str
    impacts: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class JobRequest(BaseModel):
    year: int = 2022
    language: str = "Deutsch"
    selection: Selection = Field(default_factory=Selection)
    analysis: Analysis


class JobStatus(BaseModel):
    job_id: str
    state: Literal["queued", "running", "done", "failed"]
    progress: float = 0.0
    message: Optional[str] = None

