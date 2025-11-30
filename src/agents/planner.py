import uuid
import google.generativeai as genai
from src.agents.researcher import ResearcherAgent
from src.agents.analyst import AnalystAgent
from src.agents.coder import CoderAgent
from src.agents.reviewer import ReviewerAgent
from src.memory import FileBasedMemory
from src.logger import log_agent_action

class PlannerAgent:
    def __init__(self, model_name='gemini-1.5-pro-latest'):
        self.model = genai.GenerativeModel(model_name)
        self.researcher = ResearcherAgent(model_name)
        self.analyst = AnalystAgent(model_name)
        self.coder = CoderAgent(model_name)
        self.reviewer = ReviewerAgent(model_name)
        self.memory = FileBasedMemory()

    def execute_workflow(self, user_query: str, session_id: str = None) -> str:
        """
        Orchestrates the workflow: Research -> Plan -> Analyze/Code -> Review.
        """
        if not session_id:
            session_id = str(uuid.uuid4())
            
        log_agent_action("PlannerAgent", "Start Workflow", {"query": user_query, "session_id": session_id})
        self.memory.add_history(session_id, "user", user_query)

        # Step 1: Research (Parallelizable in theory, sequential here for simplicity)
        print(f"--- Starting Research for: {user_query} ---")
        research_summary = self.researcher.research_phenotype(user_query)
        self.memory.update_session(session_id, "research", research_summary)
        print(f"--- Research Summary ---\n{research_summary}\n")
        
        # Step 2: Plan
        print("--- Creating Analysis Plan ---")
        plan_prompt = f"""
        Based on the user query and research, create a plan.
        
        Query: {user_query}
        Research: {research_summary}
        
        Decide if this requires:
        A) Standard Analysis (Drug Response, BLUP) -> Use Analyst Agent.
        B) Custom/Complex Query (e.g., "BMI > 40", specific counts) -> Use Coder Agent.
        
        Return "A" or "B" followed by the detailed plan.
        """
        plan_response = self.model.generate_content(plan_prompt)
        plan = plan_response.text
        self.memory.update_session(session_id, "plan", plan)
        print(f"--- Plan ---\n{plan}\n")
        
        # Step 3: Execution
        result = ""
        if "B" in plan[:10]: # Heuristic check
            print("--- Executing Custom Code (Coder Loop) ---")
            # Loop Pattern: Code -> Review -> Fix
            max_retries = 3
            for i in range(max_retries):
                code_result = self.coder.solve_problem(user_query, research_summary)
                review = self.reviewer.review_result(user_query, code_result)
                
                if "APPROVED" in review:
                    result = code_result
                    break
                else:
                    print(f"Review failed: {review}. Retrying...")
                    # Update context for next retry (simplified)
                    user_query += f" (Previous attempt failed: {review})"
            
            if not result:
                result = "Failed to generate valid code after retries."
        else:
            print("--- Executing Standard Analysis ---")
            result = self.analyst.perform_analysis(plan)
            
        print(f"--- Final Result ---\n{result}\n")
        self.memory.add_history(session_id, "agent", result)
        
        return result

if __name__ == "__main__":
    # Test
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if os.getenv("VERTEX_API_KEY"):
        genai.configure(api_key=os.getenv("VERTEX_API_KEY"))
        planner = PlannerAgent()
        planner.execute_workflow("How many patients prescribed statins have BMI over 40?")
