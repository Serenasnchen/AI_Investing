"""
PrivateCompanySearchProvider: company-specific web search for private company research.

Three implementations:
  DuckDuckGoPrivateCompanySearchProvider — free web search via duckduckgo-search library
  FileBackedPrivateCompanySearchProvider — offline fallback: load results from a JSON file
  MockPrivateCompanySearchProvider       — returns empty results (used in mock mode)

Source type taxonomy:
  company_official  — company's own website or investor relations page
  press_release     — PR wires (prnewswire, businesswire, globenewswire, etc.)
  research          — peer-reviewed academic sources
  regulatory        — SEC filings, ClinicalTrials.gov, FDA, EMA
  media             — news articles, blogs, analyst coverage
  unknown           — unclassifiable

Source reliability ranking (used by DiligenceAgent to grade evidence quality):
  high         — company_official, regulatory
  medium-high  — press_release, research
  medium       — media
  low          — unknown

FileBackedProvider JSON schema (data/raw/private_company_search.json):
{
  "sector_results": [
    {"title": "...", "url": "...", "snippet": "...", "published_date": "YYYY-MM-DD"}
  ],
  "company_results": {
    "Isomorphic Labs": [
      {"title": "...", "url": "...", "snippet": "...", "published_date": "YYYY-MM-DD"}
    ]
  }
}
"""
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ── Source type / reliability tables ─────────────────────────────────────────

_PRESS_RELEASE_DOMAINS = frozenset({
    "prnewswire.com",
    "businesswire.com",
    "globenewswire.com",
    "accesswire.com",
    "newswire.ca",
    "einpresswire.com",
})

_RESEARCH_DOMAINS = frozenset({
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "biorxiv.org",
    "arxiv.org",
    "nature.com",
    "science.org",
    "nejm.org",
    "jama.org",
    "cell.com",
    "thelancet.com",
    "bmj.com",
    "pubs.acs.org",
    "rsc.org",
})

_REGULATORY_DOMAINS = frozenset({
    "sec.gov",
    "edgar.sec.gov",
    "clinicaltrials.gov",
    "fda.gov",
    "ema.europa.eu",
    "investor.gov",
    "nmpa.gov.cn",
})

SOURCE_RELIABILITY: Dict[str, str] = {
    "company_official": "high",
    "regulatory": "high",
    "press_release": "medium-high",
    "research": "medium-high",
    "media": "medium",
    "unknown": "low",
}


def classify_source(url: str, company_name: str = "") -> Tuple[str, str]:
    """
    Return (source_type, reliability) for a given URL.

    Heuristics (applied in priority order):
      1. Regulatory domains  → regulatory / high
      2. Press-release wires → press_release / medium-high
      3. Academic domains    → research / medium-high
      4. Company name in domain (simplified match) → company_official / high
      5. Everything else     → media / medium
    """
    if not url:
        return "unknown", "low"

    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return "unknown", "low"

    if any(d in domain for d in _REGULATORY_DOMAINS):
        return "regulatory", "high"
    if any(d in domain for d in _PRESS_RELEASE_DOMAINS):
        return "press_release", "medium-high"
    if any(d in domain for d in _RESEARCH_DOMAINS):
        return "research", "medium-high"

    # Heuristic: if a significant word from the company name appears in the
    # domain it is likely an official company website.
    if company_name:
        name_words = [w.lower() for w in company_name.split() if len(w) > 3]
        if any(word in domain for word in name_words):
            return "company_official", "high"

    return "media", "medium"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class PrivateCompanySearchResult:
    """A single search result enriched with source-type metadata."""

    title: str
    url: str
    snippet: str
    source_name: str           # domain or publication name
    source_type: str           # company_official | press_release | media | research | regulatory | unknown
    reliability: str           # high | medium-high | medium | low
    published_date: Optional[str] = None


# ── Abstract base class ───────────────────────────────────────────────────────

class PrivateCompanySearchProvider(ABC):
    """Abstract interface for private company research via web search."""

    @abstractmethod
    def search_company(
        self,
        company_name: str,
        num_results: int = 6,
    ) -> List[PrivateCompanySearchResult]:
        """
        Search for a specific private company by name.
        Returns results ranked by relevance, enriched with source_type.
        """
        ...

    @abstractmethod
    def search_sector(
        self,
        sector: str,
        query_suffix: str = "",
        num_results: int = 10,
    ) -> List[PrivateCompanySearchResult]:
        """
        Search for private companies active in a sector.
        Used by SourcingAgent for candidate discovery.
        """
        ...


# ── DuckDuckGo implementation (free, no API key) ──────────────────────────────

class DuckDuckGoPrivateCompanySearchProvider(PrivateCompanySearchProvider):
    """
    Uses the `duckduckgo-search` library for free web search.
    No API key required.

    Install: pip install duckduckgo-search
    """

    # Extra search terms appended to company searches to surface relevant pages
    _COMPANY_QUERY_SUFFIX = (
        "funding valuation series pipeline technology biotech site:crunchbase.com OR "
        "site:techcrunch.com OR site:prnewswire.com OR site:businesswire.com OR "
        "site:sec.gov OR site:clinicaltrials.gov"
    )

    def search_company(
        self,
        company_name: str,
        num_results: int = 6,
    ) -> List[PrivateCompanySearchResult]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error(
                "[DuckDuckGoProvider] duckduckgo-search not installed. "
                "Run: pip install duckduckgo-search"
            )
            return []

        query = f"{company_name} {self._COMPANY_QUERY_SUFFIX}"
        try:
            raw = list(DDGS().text(query, max_results=num_results))
            results = [self._convert(r, company_name) for r in raw]
            logger.info(
                "[DuckDuckGoProvider] search_company('%s') → %d results.",
                company_name,
                len(results),
            )
            return results
        except Exception as exc:
            logger.warning(
                "[DuckDuckGoProvider] search_company('%s') failed: %s", company_name, exc
            )
            return []

    def search_sector(
        self,
        sector: str,
        query_suffix: str = "",
        num_results: int = 10,
    ) -> List[PrivateCompanySearchResult]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error(
                "[DuckDuckGoProvider] duckduckgo-search not installed. "
                "Run: pip install duckduckgo-search"
            )
            return []

        query = f"{sector} private startup funding 2023 2024 {query_suffix}".strip()
        try:
            raw = list(DDGS().text(query, max_results=num_results))
            results = [self._convert(r) for r in raw]
            logger.info(
                "[DuckDuckGoProvider] search_sector('%s') → %d results.",
                sector,
                len(results),
            )
            return results
        except Exception as exc:
            logger.warning(
                "[DuckDuckGoProvider] search_sector('%s') failed: %s", sector, exc
            )
            return []

    @staticmethod
    def _convert(raw: dict, company_name: str = "") -> PrivateCompanySearchResult:
        url = raw.get("href", raw.get("url", ""))
        source_type, reliability = classify_source(url, company_name)
        domain = urlparse(url).netloc.lstrip("www.") if url else "unknown"
        return PrivateCompanySearchResult(
            title=raw.get("title", ""),
            url=url,
            snippet=raw.get("body", raw.get("snippet", "")),
            source_name=domain,
            source_type=source_type,
            reliability=reliability,
            published_date=raw.get("published_date"),
        )


# ── File-backed implementation (offline / manual import) ──────────────────────

class FileBackedPrivateCompanySearchProvider(PrivateCompanySearchProvider):
    """
    Loads pre-collected search results from a local JSON file.

    Useful when:
      - No internet access is available during a pipeline run
      - A researcher wants to pre-fetch and curate results manually
      - Testing with deterministic real-world data

    Expected file: data/raw/private_company_search.json
    Schema:
    {
      "sector_results": [
        {"title": "...", "url": "...", "snippet": "...", "published_date": "YYYY-MM-DD"}
      ],
      "company_results": {
        "Company Name": [
          {"title": "...", "url": "...", "snippet": "...", "published_date": "YYYY-MM-DD"}
        ]
      }
    }
    """

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._data: Optional[dict] = None

    def _load(self) -> dict:
        if self._data is None:
            if not self.data_path.exists():
                logger.warning(
                    "[FileBackedProvider] Data file not found at %s. "
                    "Create data/raw/private_company_search.json to use this provider. "
                    "Returning empty results.",
                    self.data_path,
                )
                self._data = {}
            else:
                self._data = json.loads(self.data_path.read_text(encoding="utf-8"))
                logger.info("[FileBackedProvider] Loaded search data from %s.", self.data_path.name)
        return self._data

    def search_company(
        self,
        company_name: str,
        num_results: int = 6,
    ) -> List[PrivateCompanySearchResult]:
        data = self._load()
        raw_list = data.get("company_results", {}).get(company_name, [])
        results = [self._convert(r, company_name) for r in raw_list[:num_results]]
        logger.info(
            "[FileBackedProvider] search_company('%s') → %d results.", company_name, len(results)
        )
        return results

    def search_sector(
        self,
        sector: str,
        query_suffix: str = "",
        num_results: int = 10,
    ) -> List[PrivateCompanySearchResult]:
        data = self._load()
        raw_list = data.get("sector_results", [])
        results = [self._convert(r) for r in raw_list[:num_results]]
        logger.info(
            "[FileBackedProvider] search_sector('%s') → %d results.", sector, len(results)
        )
        return results

    @staticmethod
    def _convert(r: dict, company_name: str = "") -> PrivateCompanySearchResult:
        url = r.get("url", "")
        source_type, reliability = classify_source(url, company_name)
        domain = urlparse(url).netloc.lstrip("www.") if url else "unknown"
        return PrivateCompanySearchResult(
            title=r.get("title", ""),
            url=url,
            snippet=r.get("snippet", ""),
            source_name=r.get("source_name", domain),
            source_type=source_type,
            reliability=reliability,
            published_date=r.get("published_date"),
        )


# ── Mock implementation ───────────────────────────────────────────────────────

class MockPrivateCompanySearchProvider(PrivateCompanySearchProvider):
    """
    Stub for mock / offline mode.
    Returns no results so agents fall back to sourcing-provided evidence.
    """

    def search_company(
        self,
        company_name: str,
        num_results: int = 6,
    ) -> List[PrivateCompanySearchResult]:
        logger.debug(
            "[MockPrivateCompanySearchProvider] No real data for '%s' — returning [].",
            company_name,
        )
        return []

    def search_sector(
        self,
        sector: str,
        query_suffix: str = "",
        num_results: int = 10,
    ) -> List[PrivateCompanySearchResult]:
        logger.debug(
            "[MockPrivateCompanySearchProvider] No real data for sector '%s' — returning [].",
            sector,
        )
        return []


# ── Formatting helper (shared by SourcingAgent and DiligenceAgent) ────────────

def format_search_results_for_llm(
    results: List[PrivateCompanySearchResult],
    header: str = "Web search results",
) -> str:
    """
    Render a list of PrivateCompanySearchResult into a text block for LLM prompts.

    Output format per result:
      [N] SOURCE_TYPE (reliability) — source_name
      Title: ...
      URL: ...
      Date: ...
      Snippet: ...
    """
    if not results:
        return f"## {header}\n\nNo results available."

    lines = [f"## {header}", ""]
    for i, r in enumerate(results, 1):
        date_str = f"  |  Date: {r.published_date}" if r.published_date else ""
        lines.append(
            f"[{i}] {r.source_type.upper()} (reliability: {r.reliability})"
            f" — {r.source_name}{date_str}"
        )
        lines.append(f"Title: {r.title}")
        lines.append(f"URL: {r.url}")
        lines.append(f"Snippet: {r.snippet}")
        lines.append("")
    return "\n".join(lines)
