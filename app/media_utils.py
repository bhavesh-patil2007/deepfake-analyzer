"""Media validation and helper utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union

DEFAULT_MAX_UPLOAD_MB = 100

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

MediaKind = Literal["image", "video"]


class MediaValidationError(ValueError):
    """Raised when a media file does not meet input requirements."""


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    extension: str
    size_bytes: int
    media_type: MediaKind


def get_media_type(extension: str) -> MediaKind:
    normalized = extension.lower()
    if normalized in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    if normalized in SUPPORTED_VIDEO_EXTENSIONS:
        return "video"
    raise MediaValidationError(
        f"Unsupported file type '{extension}'. Supported extensions: "
        f"{', '.join(sorted(SUPPORTED_MEDIA_EXTENSIONS))}."
    )


def validate_upload_filename(filename: Optional[str]) -> str:
    """Validate an upload filename and return its normalized extension."""

    if not filename:
        raise MediaValidationError("Uploaded file must include a filename.")

    extension = Path(filename).suffix.lower()
    if not extension:
        raise MediaValidationError("Uploaded file must include a supported extension.")

    get_media_type(extension)
    return extension


def validate_media_path(file_path: Union[str, Path], max_mb: int = DEFAULT_MAX_UPLOAD_MB) -> MediaInfo:
    """Validate media extension and size, returning normalized file metadata."""

    path = Path(file_path).expanduser()
    if not path.exists():
        raise MediaValidationError(f"File does not exist: {path}")
    if not path.is_file():
        raise MediaValidationError(f"Path is not a file: {path}")

    extension = path.suffix.lower()
    media_type = get_media_type(extension)

    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise MediaValidationError("File is empty.")

    max_bytes = max_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise MediaValidationError(
            f"File is {size_bytes / (1024 * 1024):.2f} MB, which exceeds the "
            f"{max_mb} MB limit."
        )

    return MediaInfo(
        path=path,
        extension=extension,
        size_bytes=size_bytes,
        media_type=media_type,
    )


def extract_video_frames(
    video_path: Union[str, Path],
    output_dir: Union[str, Path],
    max_frames: int = 12,
) -> list[Path]:
    """Extract evenly spaced JPEG frames from a video for future analysis flows."""

    if max_frames <= 0:
        raise MediaValidationError("max_frames must be greater than zero.")

    info = validate_media_path(video_path)
    if info.media_type != "video":
        raise MediaValidationError("Frame extraction requires a video file.")

    import cv2
    import numpy as np

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(info.path))
    if not capture.isOpened():
        raise MediaValidationError(f"Could not open video file: {info.path}")

    written: list[Path] = []
    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count > 0:
            sample_count = min(max_frames, frame_count)
            frame_indices = sorted(
                set(np.linspace(0, frame_count - 1, num=sample_count, dtype=int).tolist())
            )
            for index in frame_indices:
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok:
                    continue
                frame_path = output_path / f"frame_{len(written) + 1:04d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                written.append(frame_path)
        else:
            while len(written) < max_frames:
                ok, frame = capture.read()
                if not ok:
                    break
                frame_path = output_path / f"frame_{len(written) + 1:04d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                written.append(frame_path)
    finally:
        capture.release()

    if not written:
        raise MediaValidationError("No frames could be extracted from the video.")

    return written
