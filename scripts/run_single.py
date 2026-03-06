#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_to_assets.main import run_single_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run VideoToAssets on a single URL")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume mode")
    parser.add_argument(
        "--tasks",
        action="append",
        help="Tasks to run: summary,wechat,xhs,highlights,all (repeatable/comma-separated)",
    )
    args = parser.parse_args()
    run_single_url(args.url, resume=not args.no_resume, tasks=args.tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
