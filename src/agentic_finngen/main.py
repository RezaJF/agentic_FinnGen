"""Command-line entry point: run a query through the agentic FinnGen workflow."""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from agentic_finngen.llm import describe_providers, make_client, resolve_provider
from agentic_finngen.logger import get_logger, set_level

load_dotenv()

logger = get_logger(__name__)


def _print_models() -> int:
    """Ask the configured provider which models the current key can reach."""
    spec = resolve_provider()
    try:
        client = make_client()
    except RuntimeError as exc:
        # A missing default model still lets us list, so retry with a throwaway id.
        if "No default model" not in str(exc):
            print(exc, file=sys.stderr)
            return 1
        client = make_client(model="unused-for-listing")

    lister = getattr(client, "list_models", None)
    if lister is None:
        print(
            f"{spec.label} does not expose a model listing endpoint.",
            file=sys.stderr,
        )
        return 1

    try:
        models = lister()
    except Exception as exc:  # noqa: BLE001 - surface provider errors verbatim
        print(f"Could not list models for {spec.label}: {exc}", file=sys.stderr)
        return 1

    print(f"Models available to your {spec.label} key:")
    for model in models:
        print(f"  {model}")
    return 0


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
        "--provider",
        help=(
            "LLM provider to use for this run (overrides LLM_PROVIDER). "
            "See --list-providers."
        ),
    )
    parser.add_argument(
        "--model",
        help="Model id to use for this run (overrides LLM_MODEL).",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="Print the supported providers and the API key each one expects.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print the models the configured provider offers your API key.",
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

    # Both overrides feed the same env vars the agents read, so every agent in
    # the workflow picks up the choice rather than only the entry point.
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["LLM_MODEL"] = args.model

    if args.list_providers:
        print(describe_providers())
        return 0

    if args.list_models:
        return _print_models()

    if args.query is None or args.query == "-":
        query = sys.stdin.read().strip()
    else:
        query = args.query

    if not query:
        parser.error("query is empty")

    spec = resolve_provider()
    logger.info(
        "Running query via %s (%s): %s in session %s",
        spec.label,
        os.getenv("LLM_MODEL") or spec.default_model,
        query,
        args.session_id,
    )
    from agentic_finngen.agents.planner import PlannerAgent

    result = PlannerAgent().execute_workflow(query, session_id=args.session_id)
    logger.info(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
