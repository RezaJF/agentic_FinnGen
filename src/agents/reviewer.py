import google.generativeai as genai
from src.logger import log_agent_action

class ReviewerAgent:
    def __init__(self, model_name='gemini-1.5-pro-latest'):
        self.model = genai.GenerativeModel(model_name)

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
        
        response = self.model.generate_content(prompt)
        log_agent_action("ReviewerAgent", "Verdict", response.text)
        return response.text
