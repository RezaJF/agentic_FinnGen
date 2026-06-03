import functools
import os
import sys
from typing import Callable, List

from agentic_finngen.llm.base import Tool
from agentic_finngen.logger import get_logger

logger = get_logger(__name__)

# Add the sibling repo to path to import fganalysis_mcp
# In a production env, this would be installed via pip
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../fganalysis_MCP")))

try:
    from fganalysis_mcp.server import (
        run_drug_response_analysis,
        run_blup_analysis,
        get_lab_data_summary,
        get_drug_purchases,
        plot_lab_distribution,
        execute_r_code,
    )
except ImportError as exc:
    # Fallback: log the stack trace for debugging, but continue with dummy tools
    # that return error messages.
    logger.debug("fganalysis_mcp import failed", exc_info=True)
    logger.warning(
        "fganalysis_mcp not found. %s. All tools will return an error message instead.",
        exc,
    )
    def run_drug_response_analysis(*args, **kwargs): return "Error"
    def run_blup_analysis(*args, **kwargs): return "Error"
    def get_lab_data_summary(*args, **kwargs): return "Error"
    def get_drug_purchases(*args, **kwargs): return "Error"
    def plot_lab_distribution(*args, **kwargs): return "Error"
    def execute_r_code(*args, **kwargs): return "Error"


def _with_db_config(fn: Callable) -> Callable:
    """Auto-inject FGANALYSIS_CONFIG_PATH into every call. Read at call time
    so callers that `load_dotenv()` after import still take effect."""

    @functools.wraps(fn)
    def wrapped(**kwargs):
        if "config_path" not in kwargs:
            cfg = os.getenv("FGANALYSIS_CONFIG_PATH")
            if cfg:
                kwargs["config_path"] = cfg
        return fn(**kwargs)

    return wrapped


_STRING_ARRAY = {"type": "array", "items": {"type": "string"}}
_NUMBER_PAIR = {
    "type": "array",
    "items": {"type": "number"},
    "minItems": 2,
    "maxItems": 2,
}


_TOOLS: List[Tool] = [
    Tool(
        name="run_drug_response_analysis",
        description=(
            "Create a fganalysis drug-response object and write summary artefacts. "
            "Compares lab values before and after drug initiation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": {**_STRING_ARRAY, "description": "OMOP lab concept IDs."},
                "drug_codes": {**_STRING_ARRAY, "description": "ATC drug codes."},
                "output_prefix": {"type": "string", "description": "Filesystem prefix for output artefacts."},
                "before_window": {**_NUMBER_PAIR, "description": "[start, end] years before drug start (default [-1, 0])."},
                "after_window": {**_NUMBER_PAIR, "description": "[start, end] years after drug start (default [0.25, 1])."},
                "filter_min_max": _NUMBER_PAIR,
                "use_lab_free_text_values": {"type": "boolean"},
                "use_only_reimbursement_drugs": {"type": "boolean"},
                "use_atc_mapping": {"type": "boolean"},
                "remove_outliers_sd": {"type": "number"},
                "finngen_ids": _STRING_ARRAY,
                "create_upset_plot": {"type": "boolean"},
            },
            "required": ["lab_id", "drug_codes", "output_prefix"],
        },
        fn=_with_db_config(run_drug_response_analysis),
    ),
    Tool(
        name="run_blup_analysis",
        description="Calculate per-individual BLUP slopes for longitudinal lab measurements.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": _STRING_ARRAY,
                "drug_codes": _STRING_ARRAY,
                "output_dir": {"type": "string"},
                "months_before": {"type": "number", "default": 3},
                "min_measurements": {"type": "integer", "default": 2},
                "include_sex": {"type": "boolean"},
                "use_freetext_values": {"type": "boolean"},
                "use_only_reimbursement": {"type": "boolean"},
                "use_atc_mapping": {"type": "boolean"},
                "remove_outliers_sd": {"type": "number"},
                "winsorize_pct": {"type": "number"},
                "calculate_qc": {"type": "boolean"},
                "save_model": {"type": "boolean"},
                "plot_blup_correlation": {"type": "boolean"},
                "output_file_prefix": {"type": "string"},
            },
            "required": ["lab_id", "drug_codes", "output_dir"],
        },
        fn=_with_db_config(run_blup_analysis),
    ),
    Tool(
        name="get_lab_data_summary",
        description="Return count and preview rows for selected OMOP lab concept IDs.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": _STRING_ARRAY,
                "require_values": {"type": "boolean"},
                "use_freetext_values": {"type": "boolean"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["lab_id"],
        },
        fn=_with_db_config(get_lab_data_summary),
    ),
    Tool(
        name="get_drug_purchases",
        description="Return count and preview rows for purchases matching ATC code prefixes.",
        input_schema={
            "type": "object",
            "properties": {
                "drug_codes": _STRING_ARRAY,
                "finngen_ids": _STRING_ARRAY,
                "use_only_reimbursement": {"type": "boolean"},
                "use_atc_mapping": {"type": "boolean"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["drug_codes"],
        },
        fn=_with_db_config(get_drug_purchases),
    ),
    Tool(
        name="plot_lab_distribution",
        description="Generate a before/after lab-value distribution plot for selected drugs.",
        input_schema={
            "type": "object",
            "properties": {
                "lab_id": _STRING_ARRAY,
                "drug_codes": _STRING_ARRAY,
                "output_file": {"type": "string"},
                "before_window": _NUMBER_PAIR,
                "after_window": _NUMBER_PAIR,
                "remove_outliers": {"type": "boolean"},
                "use_atc_mapping": {"type": "boolean"},
            },
            "required": ["lab_id", "drug_codes", "output_file"],
        },
        fn=_with_db_config(plot_lab_distribution),
    ),
    Tool(
        name="execute_r_code",
        description=(
            "Execute ad hoc R code with `conn` (database connection) and fganalysis "
            "exports already in scope. Use `print()` to surface results to stdout."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "R code to execute."},
                "timeout_seconds": {"type": "integer", "default": 300},
            },
            "required": ["code"],
        },
        fn=_with_db_config(execute_r_code),
    ),
]


def get_fganalysis_tools() -> List[Tool]:
    return list(_TOOLS)
