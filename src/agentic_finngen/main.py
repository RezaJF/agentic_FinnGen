"""Command-line entry point: run a query through the agentic FinnGen workflow."""
from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from agentic_finngen.agents.planner import PlannerAgent
from agentic_finngen.logger import get_logger, set_level

load_dotenv()

logger = get_logger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentic-finngen",
        description="Run a natural-language query through the FinnGen agent workflow.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="The question to ask. Use '-' to read from stdin. If omitted, reads stdin.",
    )
    parser.add_argument(
        "--session-id",
        help="Reuse an existing session id (otherwise a new uuid is generated).",
    )
    parser.add_argument(
        "--log-level",
        metavar="LEVEL",
        help=(
            "Override the log level (DEBUG, INFO, WARNING, ERROR). "
            "Takes precedence over the AGENTIC_FINNGEN_LOG_LEVEL env var."
        ),
    )
    args = parser.parse_args(argv)

    if args.log_level and not set_level(args.log_level):
        parser.error(f"invalid --log-level: {args.log_level!r}")

    if args.query is None or args.query == "-":
        query = sys.stdin.read().strip()
    else:
        query = args.query

    if not query:
        parser.error("query is empty")

    logger.info("Running query: %s in session %s", query, args.session_id)
    result = PlannerAgent().execute_workflow(query, session_id=args.session_id)
    logger.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
