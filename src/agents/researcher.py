import google.generativeai as genai
from src.tools.risteys_scraper import search_risteys

class ResearcherAgent:
    def __init__(self, model_name='gemini-1.5-pro-latest'):
        self.tools = [search_risteys]
        self.model = genai.GenerativeModel(model_name, tools=self.tools)
        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

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
        response = self.chat.send_message(prompt)
        return response.text
