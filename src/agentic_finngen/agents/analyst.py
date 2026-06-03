from agentic_finngen.llm import Message, make_client
from agentic_finngen.llm.loop import run_tool_loop
from agentic_finngen.tools.mcp_bridge import get_fganalysis_tools


class AnalystAgent:
    def __init__(self):
        self.client = make_client()
        self.tools = get_fganalysis_tools()

    def perform_analysis(self, plan: str) -> str:
        """
        Performs analysis based on a plan.
        """
        prompt = f"""
        You are an expert data analyst using the FinnGen `fganalysis` package.

        Plan:
        {plan}

        Execute the necessary steps using the available tools.
        If you need to run a drug response analysis, ensure you have the lab ID and drug codes.
        If you need to plot distribution, use `plot_lab_distribution`.

        Report the results and the paths to any generated files.
        """
        return run_tool_loop(
            self.client,
            messages=[Message(role="user", text=prompt)],
            tools=self.tools,
        )
