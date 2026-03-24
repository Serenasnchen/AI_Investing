"""
SearchProvider: interface for web / company search tools.

Intended real integrations:
  - Perplexity API  (sonar-pro model, grounded web search)
  - Brave Search API (https://api.search.brave.com)
  - SerpAPI / Google Custom Search

The agent layer never imports a concrete implementation directly;
it receives a SearchProvider instance injected by the orchestrator.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    """A single result returned by a search query."""
    title: str
    snippet: str
    url: str
    source: str = "web"          # "web" | "news" | "academic" | "database"
    published_date: Optional[str] = None


class SearchProvider(ABC):
    """Abstract interface for all search tools."""

    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """
        Execute a search query and return ranked results.

        Args:
            query: Natural language or keyword query.
            num_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects ordered by relevance.
        """
        ...


class RealPerplexitySearchProvider(SearchProvider):
    """
    Production implementation using the Perplexity Sonar API.

    To activate:
      1. Set PERPLEXITY_API_KEY in your .env file.
      2. pip install openai   (Perplexity uses an OpenAI-compatible endpoint)
      3. Replace the NotImplementedError body below with the real call.

    API docs: https://docs.perplexity.ai/reference/post_chat_completions
    """

    def __init__(self, api_key: str, model: str = "sonar-pro"):
        self.api_key = api_key
        self.model = model

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        raise NotImplementedError(
            "RealPerplexitySearchProvider is not yet implemented. "
            "Set USE_MOCK_PROVIDERS=true or implement the Perplexity API call here."
        )
