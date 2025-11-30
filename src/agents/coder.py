import google.generativeai as genai
from src.tools.mcp_bridge import get_fganalysis_tools
from src.logger import log_agent_action

class CoderAgent:
    def __init__(self, model_name='gemini-1.5-pro-latest'):
        # We specifically want the execute_r_code tool here
        self.tools = get_fganalysis_tools() 
        self.model = genai.GenerativeModel(model_name, tools=self.tools)
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def solve_problem(self, problem: str, context: str) -> str:
        """
        Writes and executes R code to solve a problem.
        """
        log_agent_action("CoderAgent", "Solving Problem", problem)
        
        prompt = f"""
        You are an expert R programmer and data scientist.
        Your goal is to answer the user's question by writing and executing R code using the `fganalysis` package.
        
        Context: {context}
        Problem: {problem}
        
        You have access to a tool `execute_r_code(code)`.
        The code runs in an environment where:
        - `conn` (database connection) is already available.
        - `fganalysis` and `dplyr` are loaded.
        
        Example Task: "Count patients with BMI > 30"
        Example Code:
        ```R
        # Use conn$pheno or conn$labs
        # Remember these are lazy tbls, so use collect() at the end
        # Print the result to stdout so it's captured
        
        # Example:
        # result <- conn$labs %>% filter(...) %>% count() %>% collect()
        # print(result)
        ```
        
        Write the code, execute it, and report the final answer.
        """
        
        response = self.chat.send_message(prompt)
        log_agent_action("CoderAgent", "Response", response.text)
        return response.text
