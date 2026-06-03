from dotenv import load_dotenv

from agentic_finngen.agents.planner import PlannerAgent
from agentic_finngen.logger import get_logger

logger = get_logger(__name__)


def evaluate_glp1_scenario():
    logger.info("=== Evaluating Scenario 1: GLP-1 Weight Loss ===")
    query = "Identify all individuals with GLP1 prescription who lost more than 20% their weight 1 year after initiation of the prescription."

    planner = PlannerAgent()
    result = planner.execute_workflow(query)

    logger.info("=== Evaluation Result ===")
    logger.info(result)


if __name__ == "__main__":
    load_dotenv()
    evaluate_glp1_scenario()
