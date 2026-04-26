"""Pydantic schemas for deepfake risk analysis reports."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


DeepfakeLabel = Literal[
    "likely_authentic",
    "uncertain",
    "suspicious",
    "likely_manipulated",
]

ConfidenceLevel = Literal["low", "medium", "high"]
EvidenceSeverity = Literal["low", "medium", "high"]


class EvidenceItem(BaseModel):
    """One observation supporting the risk assessment."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., min_length=1, description="Observation category")
    finding: str = Field(..., min_length=1, description="Specific observed issue")
    severity: EvidenceSeverity = Field(..., description="Relative severity")
    timestamp: Optional[str] = Field(
        default=None,
        description="Optional timestamp or time range for video evidence",
    )

    @field_validator("category", "finding", "timestamp")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped


class DeepfakeReport(BaseModel):
    """Structured output returned by Gemini and exposed by the app."""

    model_config = ConfigDict(extra="forbid")

    label: DeepfakeLabel = Field(..., description="Overall risk label")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 to 100")
    confidence: ConfidenceLevel = Field(..., description="Confidence in this assessment")
    summary: str = Field(..., min_length=1, description="Concise, uncertainty-aware summary")
    evidence: list[EvidenceItem] = Field(default_factory=list)
    limitations: list[str] = Field(
        default_factory=list,
        description="Important uncertainty, quality, and method limitations",
    )
    recommended_next_steps: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("summary must not be empty")
        return stripped

    @field_validator("limitations", "recommended_next_steps")
    @classmethod
    def strip_string_lists(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            stripped = value.strip()
            if not stripped:
                raise ValueError("list items must not be empty")
            cleaned.append(stripped)
        return cleaned
