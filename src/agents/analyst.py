import google.generativeai as genai
from src.tools.mcp_bridge import get_fganalysis_tools

class AnalystAgent:
    def __init__(self, model_name='gemini-1.5-pro-latest'):
        self.tools = get_fganalysis_tools()
        self.model = genai.GenerativeModel(model_name, tools=self.tools)
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

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
        response = self.chat.send_message(prompt)
        return response.text
