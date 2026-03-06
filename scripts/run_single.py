#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_to_assets.main import run_single_source  # noqa: E402
from video_to_assets.pipeline.input_resolver import resolve_source_input  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run VideoToAssets on a single input source")
    parser.add_argument("--url", help="Video URL (implies input_type=video if input_type omitted)")
    parser.add_argument("--input-type", choices=["video", "text", "file"], help="Input type")
    parser.add_argument("--text", help="Inline text input")
    parser.add_argument("--text-file", help="Text file input (for input_type=text)")
    parser.add_argument("--file", help="File input (txt/md/srt/vtt/json)")
    parser.add_argument("--title", help="Source title override")
    parser.add_argument("--source-name", help="Source name or publisher")
    parser.add_argument("--source-url", help="Source URL")
    parser.add_argument("--author", help="Author name")
    parser.add_argument("--publish-date", help="Publish date")
    parser.add_argument("--platform", help="Source platform")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume mode")
    parser.add_argument(
        "--tasks",
        action="append",
        help="Tasks to run: summary,wechat,xhs,highlights,all (repeatable/comma-separated)",
    )
    args = parser.parse_args()
    source = resolve_source_input(
        input_type=args.input_type,
        url=args.url,
        text=args.text,
        text_file=args.text_file,
        file=args.file,
        title=args.title,
        source_name=args.source_name,
        source_url=args.source_url,
        author=args.author,
        publish_date=args.publish_date,
        platform=args.platform,
    )
    run_single_source(source=source, resume=not args.no_resume, tasks=args.tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
