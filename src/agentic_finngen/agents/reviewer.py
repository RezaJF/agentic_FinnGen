from agentic_finngen.llm import Message, make_client
from agentic_finngen.logger import log_agent_action


class ReviewerAgent:
    def __init__(self):
        self.client = make_client()

    def review_result(self, problem: str, result: str) -> str:
        """
        Reviews the result provided by the Coder Agent.
        """
        log_agent_action("ReviewerAgent", "Reviewing", result)

        prompt = f"""
        You are a Senior Data Scientist. Review the following analysis result.

        Problem: {problem}
        Result: {result}

        Check for:
        1. Logical consistency.
        2. Whether the question was actually answered.
        3. Potential errors in the R code logic (if visible).

        If the result is satisfactory, reply with "APPROVED".
        If not, explain what is missing or wrong.
        """

        verdict = self.client.complete([Message(role="user", text=prompt)]).text
        log_agent_action("ReviewerAgent", "Verdict", verdict)
        return verdict
