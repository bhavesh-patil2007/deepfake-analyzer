"""FastAPI app for media risk analysis."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.analyzer import (
    AnalyzerConfigurationError,
    AnalyzerError,
    AnalyzerResponseError,
    analyze_media_file,
)
from app.media_utils import (
    DEFAULT_MAX_UPLOAD_MB,
    MediaValidationError,
    validate_upload_filename,
)
from app.schemas import DeepfakeReport

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Deepfake Analyzer",
    description="Uncertainty-aware synthetic media and manipulation risk analyzer.",
    version="0.1.0",
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
@app.get("/analyze", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _save_upload(upload: UploadFile, destination: Path, max_mb: int) -> Path:
    validate_upload_filename(upload.filename)

    destination.parent.mkdir(parents=True, exist_ok=True)
    max_bytes = max_mb * 1024 * 1024
    total = 0

    with destination.open("wb") as output:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise MediaValidationError(f"Uploaded file exceeds the {max_mb} MB limit.")
            output.write(chunk)

    if total == 0:
        raise MediaValidationError("Uploaded file is empty.")

    return destination


@app.post("/analyze", response_model=DeepfakeReport)
def analyze(file: UploadFile = File(...)) -> DeepfakeReport:
    try:
        extension = validate_upload_filename(file.filename)
        with tempfile.TemporaryDirectory(prefix="deepfake-analyzer-") as tmp_dir:
            safe_path = Path(tmp_dir) / f"upload{extension}"
            _save_upload(file, safe_path, DEFAULT_MAX_UPLOAD_MB)
            return analyze_media_file(safe_path)
    except MediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AnalyzerConfigurationError as exc:
        logger.warning("Analyzer configuration error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analyzer is not configured. Set GEMINI_API_KEY.",
        ) from exc
    except AnalyzerResponseError as exc:
        logger.warning("Invalid Gemini response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini returned an invalid analysis response.",
        ) from exc
    except AnalyzerError as exc:
        logger.warning("Gemini analysis failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini analysis failed.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected analyze endpoint failure")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected analysis failure.",
        ) from exc
    finally:
        file.file.close()


__all__ = ["app"]
