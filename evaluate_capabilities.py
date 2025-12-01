import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from src.agents.planner import PlannerAgent

def evaluate_glp1_scenario():
    print("\n=== Evaluating Scenario 1: GLP-1 Weight Loss ===\n")
    query = "Identify all individuals with GLP1 prescription who lost more than 20% their weight 1 year after initiation of the prescription."
    
    planner = PlannerAgent()
    result = planner.execute_workflow(query)
    
    print("\n=== Evaluation Result ===\n")
    print(result)

if __name__ == "__main__":
    load_dotenv()
    if os.getenv("VERTEX_API_KEY"):
        genai.configure(api_key=os.getenv("VERTEX_API_KEY"))
        evaluate_glp1_scenario()
    else:
        print("Error: VERTEX_API_KEY not found.")
