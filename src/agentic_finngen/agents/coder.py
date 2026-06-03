from agentic_finngen.llm import Message, make_client
from agentic_finngen.llm.loop import run_tool_loop
from agentic_finngen.logger import log_agent_action
from agentic_finngen.tools.mcp_bridge import get_fganalysis_tools


class CoderAgent:
    def __init__(self):
        self.client = make_client()
        # We specifically want the execute_r_code tool here
        self.tools = get_fganalysis_tools()

    def solve_problem(self, problem: str, context: str) -> str:
        """
        Writes and executes R code to solve a problem.
        """
        log_agent_action("CoderAgent", "Solving Problem", problem)

        prompt = f"""
        You are an expert R programmer and data scientist.
        Your goal is to answer the user's question by writing and executing R code using the `fganalysis` package.

        Always look for tools and ready made solutions first that can help you, and use them when appropriate instead of writing code 
        from scratch. 
        Don't try to do complex data manipulation in your head - write code and execute it to get the answer.

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

        result = run_tool_loop(
            self.client,
            messages=[Message(role="user", text=prompt)],
            tools=self.tools,
        )
        log_agent_action("CoderAgent", "Response", result)
        return result
