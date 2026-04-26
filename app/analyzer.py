"""Gemini-backed deepfake risk analyzer."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Union

from dotenv import load_dotenv
from google import genai
from pydantic import ValidationError

from app.media_utils import DEFAULT_MAX_UPLOAD_MB, MediaValidationError, validate_media_path
from app.prompts import DEEPFAKE_ANALYSIS_PROMPT
from app.schemas import DeepfakeReport

DEFAULT_MODEL = "gemini-2.5-flash"


class AnalyzerError(RuntimeError):
    """Base class for user-safe analyzer errors."""


class AnalyzerConfigurationError(AnalyzerError):
    """Raised when required analyzer configuration is missing."""


class AnalyzerResponseError(AnalyzerError):
    """Raised when Gemini returns an invalid or unusable response."""


def _get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise AnalyzerConfigurationError(
            "GEMINI_API_KEY is not set. Add it to your environment or a .env file."
        )
    return api_key


def create_client() -> genai.Client:
    """Create a Google GenAI client from GEMINI_API_KEY."""

    return genai.Client(api_key=_get_api_key())


def _generation_config() -> dict[str, Any]:
    return {
        "response_mime_type": "application/json",
        "response_json_schema": DeepfakeReport.model_json_schema(),
    }


def analyze_media_file(
    file_path: Union[str, Path],
    *,
    model: str = DEFAULT_MODEL,
    max_mb: int = DEFAULT_MAX_UPLOAD_MB,
) -> DeepfakeReport:
    """Validate, upload, analyze, and parse a media file."""

    try:
        media = validate_media_path(file_path, max_mb=max_mb)
    except MediaValidationError:
        raise

    client = create_client()

    try:
        uploaded_file = client.files.upload(file=str(media.path))
        response = client.models.generate_content(
            model=model,
            contents=[uploaded_file, DEEPFAKE_ANALYSIS_PROMPT],
            config=_generation_config(),
        )
    except Exception as exc:  # pragma: no cover - exercised with integration tests/mocks
        raise AnalyzerError("Gemini analysis request failed.") from exc

    response_text = getattr(response, "text", None)
    if not response_text:
        raise AnalyzerResponseError("Gemini returned an empty response.")

    try:
        return DeepfakeReport.model_validate_json(response_text)
    except ValidationError as exc:
        raise AnalyzerResponseError("Gemini returned JSON that did not match the schema.") from exc
