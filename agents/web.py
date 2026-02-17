from datetime import date
from typing import Optional

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools.duckduckgo import DuckDuckGo


class WebAgent:
    """Agent that searches the web for information using DuckDuckGo."""

    DEFAULT_MODEL_ID = "qwen3:1.7b"

    def __init__(
        self,
        model_id: Optional[str] = None,
    ):
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self._agent = self._build_agent()

    def _get_instructions(self) -> list[str]:
        today = date.today()
        return [
            "Use the DuckDuckGo search tool to find up-to-date information on the web when the user asks for facts, news, or general knowledge.",
            "Always perform a search when the user asks about current events, definitions, how-to steps, or any topic that may change over time.",
            "After retrieving search results, summarize the relevant information clearly and cite or mention the sources (e.g. 'According to ...').",
            "If multiple sources agree, you may say so; if they conflict, present the main viewpoints.",
            "Use the minimum number of search calls needed to answer the request. Prefer one or two targeted queries over many broad ones.",
            f"The current date is: {today}",
        ]

    def _get_guidelines(self) -> list[str]:
        return [
            "Always include sources when you use web search results. Do not present search results as unsourced facts.",
            "When the user asks for web/search information, you must call the search tool; do not respond with only text from memory.",
            "Keep answers focused and relevant to the user's question. Avoid unnecessary tangents.",
            "If a search returns no useful results, say so and suggest rephrasing or a different query.",
        ]

    def _build_agent(self) -> Agent:
        model = Ollama(id=self.model_id)
        return Agent(
            name="Web Agent",
            role="Web Search Agent",
            goal="Search the web for information and return accurate, sourced answers",
            description="The Web Agent searches the web for information. It uses DuckDuckGo to find current facts, news, and explanations, and always cites sources.",
            model=model,
            tools=[DuckDuckGo()],
            instructions=self._get_instructions(),
            guidelines=self._get_guidelines(),
            markdown=True,
            show_tool_calls=True,
        )

    def run(self, prompt: str, stream: bool = True) -> None:
        """Run the agent with the given prompt and print the response."""
        self._agent.print_response(prompt, stream=stream)

    @property
    def agent(self) -> Agent:
        """Access the underlying phi Agent instance."""
        return self._agent
