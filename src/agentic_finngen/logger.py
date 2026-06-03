"""Centralized logging for agentic FinnGen.

All runtime output flows through these loggers instead of bare ``print``:

- **INFO** (the default) — user-facing UI: workflow progress, final results.
- **DEBUG** — verbose internals: raw model responses, full research summaries,
  intermediate plans. Hidden unless explicitly enabled.

Enable debug output by setting the ``AGENTIC_FINNGEN_LOG_LEVEL`` environment
variable before running, e.g. ``AGENTIC_FINNGEN_LOG_LEVEL=DEBUG``. Any standard
level name works (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``); unknown values
fall back to INFO. Output goes to stdout and to ``agent_trace.log``.
"""
from typing import Any
import logging
import json
import os
import sys

from dotenv import load_dotenv

# Load ``.env`` here so the log level is available regardless of whether the
# importing module has called ``load_dotenv()`` yet. This module configures
# logging at import time, which often happens before an app's own
# ``load_dotenv()`` call runs.
load_dotenv()

_LEVEL_ENV = "AGENTIC_FINNGEN_LOG_LEVEL"
_DEFAULT_LEVEL = "INFO"


def _resolve_level() -> int:
    """Read the configured log level from the environment, defaulting to INFO."""
    raw = os.getenv(_LEVEL_ENV, _DEFAULT_LEVEL).strip().upper()
    print(f"Logging level set to {raw}")
    level = getattr(logging, raw, None)
    return level if isinstance(level, int) else logging.INFO


# Configure logging once at import time.
logging.basicConfig(
    level=_resolve_level(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_trace.log")
    ]
)

def set_level(level_name: str) -> bool:
    """Override the configured log level at runtime (e.g. from a CLI flag).

    Logging is configured once at import time, so this re-applies the level to
    the root logger and its handlers. Returns ``True`` if the level was a valid
    name and applied, ``False`` otherwise (in which case the level is unchanged).
    """
    level = getattr(logging, level_name.strip().upper(), None)
    if not isinstance(level, int):
        return False
    root = logging.getLogger()
    root.setLevel(level)
    for handler in root.handlers:
        handler.setLevel(level)
    return True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def log_agent_action(agent_name: str, action: str, details: Any):
    logger = get_logger(agent_name)
    logger.info(json.dumps({
        "agent": agent_name,
        "action": action,
        "details": details
    }))
