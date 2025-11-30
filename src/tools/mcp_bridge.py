import os
import sys
import json
from typing import List, Dict, Any

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
        execute_r_code
    )
except ImportError:
    # Fallback
    print("Warning: fganalysis_mcp not found.")
    def run_drug_response_analysis(*args, **kwargs): return "Error"
    def run_blup_analysis(*args, **kwargs): return "Error"
    def get_lab_data_summary(*args, **kwargs): return "Error"
    def get_drug_purchases(*args, **kwargs): return "Error"
    def plot_lab_distribution(*args, **kwargs): return "Error"
    def execute_r_code(*args, **kwargs): return "Error"

def get_fganalysis_tools():
    return [
        run_drug_response_analysis,
        run_blup_analysis,
        get_lab_data_summary,
        get_drug_purchases,
        plot_lab_distribution,
        execute_r_code
    ]
