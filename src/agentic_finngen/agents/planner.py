import uuid

from agentic_finngen.agents.researcher import ResearcherAgent
from agentic_finngen.agents.analyst import AnalystAgent
from agentic_finngen.agents.coder import CoderAgent
from agentic_finngen.agents.reviewer import ReviewerAgent
from agentic_finngen.llm import Message, make_client
from agentic_finngen.memory import FileBasedMemory
from agentic_finngen.logger import get_logger, log_agent_action

logger = get_logger(__name__)


class PlannerAgent:
    def __init__(self):
        self.client = make_client()
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()
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
        logger.info("--- Starting Research for: %s ---", user_query)
        research_summary = self.researcher.research_phenotype(user_query)
        self.memory.update_session(session_id, "research", research_summary)
        logger.info("--- Research Summary ---\n%s\n", research_summary)

        # Step 2: Plan
        logger.info("--- Creating Analysis Plan ---")
        plan_prompt = f"""
        Based on the user query and research, create a plan.

        Query: {user_query}
        Research: {research_summary}

        Decide if this requires:
        A) Standard Analysis (Drug Response, BLUP) -> Use Analyst Agent.
        B) Custom/Complex Query (e.g., "BMI > 40", specific counts) -> Use Coder Agent.

        Return "A" or "B" followed by the detailed plan.
        """
        plan = self.client.complete([Message(role="user", text=plan_prompt)]).text
        self.memory.update_session(session_id, "plan", plan)
        logger.info("--- Plan ---\n%s\n", plan)

        # Step 3: Execution
        result = ""
        if "B" in plan[:10]:  # Heuristic check
            logger.info("--- Executing Custom Code (Coder Loop) ---")
            # Loop Pattern: Code -> Review -> Fix
            max_retries = 3
            for i in range(max_retries):
                code_result = self.coder.solve_problem(user_query, research_summary)
                review = self.reviewer.review_result(user_query, code_result)

                if "APPROVED" in review:
                    result = code_result
                    break
                else:
                    logger.info("Review failed: %s. Retrying...", review)
                    # Update context for next retry (simplified)
                    user_query += f" (Previous attempt failed: {review})"

            if not result:
                result = "Failed to generate valid code after retries."
        else:
            logger.info("--- Executing Standard Analysis ---")
            result = self.analyst.perform_analysis(plan)

        logger.info("--- Final Result ---\n%s\n", result)
        self.memory.add_history(session_id, "agent", result)

        return result


if __name__ == "__main__":
    from agentic_finngen.main import main
    raise SystemExit(main())
