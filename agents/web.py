import json
from datetime import date
from typing import Any, Optional

from phi.agent import Agent
from phi.model.ollama import Ollama
from phi.tools import Toolkit

try:
    from ddgs import DDGS
except ImportError:
    raise ImportError("`ddgs` not installed. Please install using `pip install ddgs`")


class DuckDuckGo(Toolkit):
    """
    DuckDuckGo toolkit using the ddgs package. Use for web search and news.

    Args:
        search (bool): Enable DuckDuckGo search function.
        news (bool): Enable DuckDuckGo news function.
        fixed_max_results (Optional[int]): A fixed number of maximum results.
        timeout (Optional[int]): The maximum number of seconds to wait for a response.
    """

    def __init__(
        self,
        search: bool = True,
        news: bool = True,
        modifier: Optional[str] = None,
        fixed_max_results: Optional[int] = None,
        timeout: Optional[int] = 10,
        verify_ssl: bool = True,
        **kwargs: Any,
    ):
        super().__init__(name="duckduckgo")
        self.timeout = timeout
        self.fixed_max_results = fixed_max_results
        self.modifier = modifier
        self.verify_ssl = verify_ssl
        if search:
            self.register(self.duckduckgo_search)
        if news:
            self.register(self.duckduckgo_news)

    def duckduckgo_search(self, query: str, max_results: int = 5) -> str:
        """Use this function to search DuckDuckGo for a query.

        Args:
            query: The query to search for.
            max_results: The maximum number of results to return (default 5).

        Returns:
            The result from DuckDuckGo as JSON.
        """
        ddgs = DDGS(timeout=self.timeout, verify=self.verify_ssl)
        max_results = self.fixed_max_results or max_results
        keywords = f"{self.modifier} {query}".strip() if self.modifier else query
        results = ddgs.text(keywords, max_results=max_results)
        return json.dumps(results, indent=2)

    def duckduckgo_news(self, query: str, max_results: int = 5) -> str:
        """Use this function to get the latest news from DuckDuckGo.

        Args:
            query: The query to search for.
            max_results: The maximum number of results to return (default 5).

        Returns:
            The latest news from DuckDuckGo as JSON.
        """
        ddgs = DDGS(timeout=self.timeout, verify=self.verify_ssl)
        max_results = self.fixed_max_results or max_results
        results = ddgs.news(query, max_results=max_results)
        return json.dumps(results, indent=2)


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
