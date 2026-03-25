"""Pydantic schemas for the MLX drafter → writer → judge flashcard pipeline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DrafterAtom(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1, max_length=8000)
    d_conf: float = Field(ge=0.0, le=1.0)
    d_impact: float = Field(ge=0.0, le=1.0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class WriterEnriched(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1, max_length=8000)
    w_conf: float = Field(ge=0.0, le=1.0)
    w_impact: float = Field(ge=0.0, le=1.0)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class JudgeVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    j_conf: float = Field(ge=0.0, le=1.0)
    j_impact: float = Field(ge=0.0, le=1.0)
    implication: str = ""
    potential_moves: list[str] = Field(default_factory=list)

    @field_validator("potential_moves")
    @classmethod
    def cap_moves(cls, v: list[str]) -> list[str]:
        cleaned = [str(x).strip() for x in v if str(x).strip()]
        return cleaned[:3]


class TrinityFlashcardRow(BaseModel):
    """Validated row after Trinity judge math (Python-side products)."""

    model_config = ConfigDict(extra="ignore")

    drafter_text: str
    enriched_text: str
    d_conf: float
    d_impact: float
    w_conf: float
    w_impact: float
    j_conf: float
    j_impact: float
    final_confidence: float = Field(ge=0.0, le=1.0)
    final_impact: float = Field(ge=0.0, le=1.0)
    implication: str
    potential_moves: list[str]
    hybrid_gate_flags: list[str] = Field(default_factory=list)
    quarantine_reason: str | None = None
