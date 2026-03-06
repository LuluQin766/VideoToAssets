from __future__ import annotations

import argparse

from video_to_assets.main import run_single_source
from video_to_assets.pipeline.input_resolver import resolve_source_input


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video_to_assets")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a single input source")
    run_parser.add_argument("--url", help="Video URL (implies input_type=video if input_type omitted)")
    run_parser.add_argument("--input-type", choices=["video", "text", "file"], help="Input type")
    run_parser.add_argument("--text", help="Inline text input")
    run_parser.add_argument("--text-file", help="Text file input (for input_type=text)")
    run_parser.add_argument("--file", help="File input (txt/md/srt/vtt/json)")
    run_parser.add_argument("--title", help="Source title override")
    run_parser.add_argument("--source-name", help="Source name or publisher")
    run_parser.add_argument("--source-url", help="Source URL")
    run_parser.add_argument("--author", help="Author name")
    run_parser.add_argument("--publish-date", help="Publish date")
    run_parser.add_argument("--platform", help="Source platform")
    run_parser.add_argument("--no-resume", action="store_true", help="Disable resume")
    run_parser.add_argument(
        "--tasks",
        action="append",
        help="Tasks to run: summary,wechat,xhs,highlights,all (can be repeated or comma-separated)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
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

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
