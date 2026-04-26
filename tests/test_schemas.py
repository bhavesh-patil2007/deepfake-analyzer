"""Tests for DeepfakeReport schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import DeepfakeReport


def valid_report_payload() -> dict:
    return {
        "label": "uncertain",
        "risk_score": 42,
        "confidence": "medium",
        "summary": "Some minor visual anomalies are present, but the evidence is not definitive.",
        "evidence": [
            {
                "category": "lighting",
                "finding": "Shadows appear slightly inconsistent around the cheeks.",
                "severity": "low",
                "timestamp": None,
            }
        ],
        "limitations": ["Compressed media can create false positives."],
        "recommended_next_steps": ["Compare against the original source file if available."],
    }


def test_valid_report_payload_is_accepted() -> None:
    report = DeepfakeReport.model_validate(valid_report_payload())

    assert report.label == "uncertain"
    assert report.risk_score == 42
    assert report.evidence[0].severity == "low"


@pytest.mark.parametrize("score", [-1, 101])
def test_risk_score_must_be_between_zero_and_one_hundred(score: int) -> None:
    payload = valid_report_payload()
    payload["risk_score"] = score

    with pytest.raises(ValidationError):
        DeepfakeReport.model_validate(payload)


def test_label_must_be_known_value() -> None:
    payload = valid_report_payload()
    payload["label"] = "definitely_fake"

    with pytest.raises(ValidationError):
        DeepfakeReport.model_validate(payload)


def test_confidence_must_be_known_value() -> None:
    payload = valid_report_payload()
    payload["confidence"] = "certain"

    with pytest.raises(ValidationError):
        DeepfakeReport.model_validate(payload)


def test_evidence_rejects_empty_text() -> None:
    payload = valid_report_payload()
    payload["evidence"][0]["finding"] = "   "

    with pytest.raises(ValidationError):
        DeepfakeReport.model_validate(payload)


def test_extra_fields_are_rejected() -> None:
    payload = valid_report_payload()
    payload["verdict"] = "fake"

    with pytest.raises(ValidationError):
        DeepfakeReport.model_validate(payload)
