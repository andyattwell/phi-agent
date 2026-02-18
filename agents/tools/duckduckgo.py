
import json
from typing import Any, Optional

from phi.tools.toolkit import Toolkit


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
