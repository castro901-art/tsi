import math
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MatchInput(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    home_team: str | None = Field(default=None, max_length=120)
    away_team: str | None = Field(default=None, max_length=120)
    competition: str | None = Field(default=None, max_length=120)
    match_date: str | None = Field(default=None, max_length=30)
    authorised: Literal[True]
    provider_processing_consent: Literal[True]


class Candidate(StrictModel):
    event_type: Literal["goal", "shot", "save", "corner", "free_kick", "attacking_combination", "counterattack", "defensive_error", "set_piece", "other"]
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    observation: str = Field(min_length=1, max_length=1500)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_seconds < self.start_seconds:
            raise ValueError("Event end precedes start")
        return self


class Interpretation(StrictModel):
    section: Literal["attacking", "defensive", "set_piece", "match_interpretation"]
    text: str = Field(min_length=1, max_length=2000)
    event_indices: list[int] = Field(min_length=1, max_length=20)


class Findings(StrictModel):
    events: list[Candidate] = Field(max_length=100)
    interpretations: list[Interpretation] = Field(max_length=30)
    limitations: list[str] = Field(max_length=20)

    def validate_evidence(self, duration: float):
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Invalid video duration")
        for event in self.events:
            if event.end_seconds > duration:
                raise ValueError("Event exceeds source duration")
        for claim in self.interpretations:
            if any(i < 0 or i >= len(self.events) for i in claim.event_indices):
                raise ValueError("Interpretation references missing evidence")
        return self
