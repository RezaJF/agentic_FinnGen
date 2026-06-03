from agentic_finngen.llm import Message, make_client
from agentic_finngen.llm.loop import run_tool_loop
from agentic_finngen.tools.risteys_scraper import search_risteys_tool


class ResearcherAgent:
    def __init__(self):
        self.client = make_client()
        self.tools = [search_risteys_tool]

    def research_phenotype(self, query: str) -> str:
        """
        Researches a phenotype using Risteys.
        """
        prompt = f"""
        You are a biomedical researcher. Your goal is to find information about a phenotype using the Risteys database.

        User Query: {query}

        Steps:
        1. Search for the phenotype code or name using the `search_risteys` tool.
        2. Summarize the findings, including the description and key statistics (n_cases, etc.).
        3. Return a concise summary.
        """
        return run_tool_loop(
            self.client,
            messages=[Message(role="user", text=prompt)],
            tools=self.tools,
        )
