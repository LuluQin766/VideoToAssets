from __future__ import annotations

import argparse

from video_to_assets.main import run_single_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video_to_assets")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a single video URL")
    run_parser.add_argument("--url", required=True, help="Video URL")
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
        run_single_url(url=args.url, resume=not args.no_resume, tasks=args.tasks)
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
