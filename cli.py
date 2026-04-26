"""Command-line interface for Deepfake Analyzer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from app.analyzer import AnalyzerError, analyze_media_file
from app.media_utils import DEFAULT_MAX_UPLOAD_MB, MediaValidationError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze an image or video for possible synthetic media risk."
    )
    parser.add_argument("file", help="Path to an image or video file.")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model to use. Defaults to gemini-2.5-flash.",
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        default=DEFAULT_MAX_UPLOAD_MB,
        help=f"Maximum input file size in MB. Defaults to {DEFAULT_MAX_UPLOAD_MB}.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        report = analyze_media_file(Path(args.file), model=args.model, max_mb=args.max_mb)
    except MediaValidationError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    except AnalyzerError as exc:
        print(f"Analysis error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
