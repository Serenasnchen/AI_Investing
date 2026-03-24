"""
SourcingAgent: discovers and pre-screens private companies in the target sector.

Two-step pipeline:
  1. TOOL LAYER  — SearchProvider fetches raw search results (Perplexity / Brave / mock)
  2. AGENT LAYER — LLM deduplicates, classifies, scores (5 dimensions), and ranks results

This design separates data retrieval (provider) from reasoning (LLM), making it easy
to swap the search backend without touching any analysis logic.

Output: List[StartupScreeningResult] — each entry wraps a StartupProfile with
        a 5-dimension pre-screening scorecard and a priority rank.
"""
import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from src.config import SectorConfig
from src.models.company import DimensionScore, StartupProfile, StartupScreeningResult
from src.providers.search_provider import SearchProvider, SearchResult
from src.providers.private_company_search_provider import (
    PrivateCompanySearchProvider,
    PrivateCompanySearchResult,
    format_search_results_for_llm,
)
from .base_agent import BaseAgent, is_placeholder_url

# Tie-break order when total_score is equal: work through dimensions in this
# order (highest score wins at each step), then fall back to name (A < Z).
_TIEBREAK_DIMS = [
    "tech_frontier",
    "commercialization_potential",
    "data_flywheel",
    "team_credibility",
    "information_completeness",
]


def _rank_key(r: StartupScreeningResult) -> Tuple:
    """
    Sort key for descending-score ordering with deterministic tie-breaking.

    Returns a tuple of:
      (-total_score, -tech_frontier, -commercialization_potential,
       -data_flywheel, -team_credibility, -information_completeness, name)

    Negating numeric scores lets Python's default ascending sort produce the
    desired descending-score result without a reverse=True flag (which would
    flip the string comparison for name).
    """
    _zero = DimensionScore(score=0.0, rationale="")
    dim_negs = tuple(
        -r.dimension_scores.get(d, _zero).score for d in _TIEBREAK_DIMS
    )
    return (-r.total_score,) + dim_negs + (r.startup.name,)

logger = logging.getLogger(__name__)


class SourcingAgent(BaseAgent):
    """
    Responsibilities:
    - Query SearchProvider with sector-specific queries to collect raw candidate signals
    - Use LLM to deduplicate, filter to private companies only, classify technology
      approaches, score each company on 5 pre-screening dimensions, and return a
      ranked shortlist of StartupScreeningResult objects
    """

    prompt_file = "sourcing.md"

    def __init__(
        self,
        config: SectorConfig,
        search_provider: SearchProvider,
        private_search_provider: Optional[PrivateCompanySearchProvider] = None,
    ):
        super().__init__(config)
        self.search_provider = search_provider
        self.private_search_provider = private_search_provider

    def run(self, output_dir: Optional[Path] = None) -> List[StartupScreeningResult]:
        """
        Run the full sourcing + pre-screening pipeline.

        Args:
            output_dir: run-specific directory (e.g. data/processed/{run_id}/).
                        If provided, the full screening results are saved there as
                        sourcing_screening_results.json in addition to the orchestrator's
                        startup_profiles.json.

        Returns:
            List[StartupScreeningResult] sorted by total_score descending (priority_rank 1 = best).
        """
        # --- Step 1: Tool layer — retrieve raw signals from search provider ---
        raw_results = self._fetch_search_signals()

        if not raw_results:
            logger.warning("[SourcingAgent] Search provider returned no results.")
            return []

        # --- Step 2: Agent layer — LLM structures, classifies, scores, ranks ---
        formatted_context = self._format_search_results(raw_results)
        known_public_note = self._build_known_public_note()
        prompt = self._render_prompt(
            raw_search_results=formatted_context,
            target_count=self.config.sourcing_target_count,
            known_public_tickers_note=known_public_note,
        )
        raw = self._call_llm(
            user_prompt=prompt,
            system_prompt=(
                "You are a venture capital analyst specializing in deep tech and biotech. "
                "Return your answer ONLY as a valid JSON array — no prose, no markdown fences."
            ),
        )

        try:
            data = self._parse_json(raw)
            # Strip placeholder URLs from source_urls before constructing models
            data = [self._clean_source_urls(item) for item in data]
            results = [StartupScreeningResult(**item) for item in data]

            # Post-processing filter: remove any company that is already public
            # (status == "ipo") or whose name is suspiciously close to a known
            # public ticker covered by the public market agent.
            results = self._filter_public_companies(results)

            # Sort by total_score descending; tie-break by dimension scores
            # (tech_frontier → … → information_completeness) then name A→Z.
            results.sort(key=_rank_key)

            # Assign sequential 1-based priority_rank after sorting so rank
            # always reflects the actual score ordering, regardless of what
            # order the LLM returned items in.
            for i, r in enumerate(results, 1):
                r.priority_rank = i

            logger.info(
                "[SourcingAgent] Screened %d companies from %d search results.",
                len(results),
                len(raw_results),
            )
            if output_dir is not None:
                self._save_screening_results(results, output_dir)
            return results
        except Exception as exc:
            logger.error("[SourcingAgent] Failed to parse LLM response: %s", exc)
            logger.debug("Raw response: %s", raw)
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_search_signals(self) -> List[SearchResult]:
        """
        Run 2 complementary queries and combine deduplicated results.

        If a PrivateCompanySearchProvider is available, its sector search
        results are used as the primary source (they carry source_type metadata
        that helps the LLM assess evidence quality).  The plain SearchProvider
        is used as a fallback or supplemental source.
        """
        sector = self.config.sector

        # ── Primary: PrivateCompanySearchProvider (typed sources) ────────────
        if self.private_search_provider is not None:
            rich = self.private_search_provider.search_sector(
                sector,
                query_suffix="private startup funding venture capital",
                num_results=12,
            )
            if rich:
                # Convert to SearchResult for downstream compatibility, preserving
                # source_type in the source field for LLM context
                seen_urls: set = set()
                combined: List[SearchResult] = []
                for r in rich:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        combined.append(
                            SearchResult(
                                title=r.title,
                                snippet=r.snippet,
                                url=r.url,
                                source=f"{r.source_type}:{r.reliability}",
                                published_date=r.published_date,
                            )
                        )
                logger.info(
                    "[SourcingAgent] Fetched %d unique results from PrivateCompanySearchProvider.",
                    len(combined),
                )
                return combined

        # ── Fallback: plain SearchProvider ───────────────────────────────────
        queries = [
            f"{sector} private company startup funding 2023 2024",
            f"{sector} machine learning platform venture capital investment",
        ]
        seen_urls = set()
        combined = []
        for query in queries:
            results = self.search_provider.search(query, num_results=10)
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    combined.append(r)
        logger.info(
            "[SourcingAgent] Fetched %d unique search results via SearchProvider fallback.",
            len(combined),
        )
        return combined

    @staticmethod
    def _clean_source_urls(item: dict) -> dict:
        """Remove placeholder URLs from startup.source_urls before model construction."""
        startup = item.get("startup", {})
        raw_urls = startup.get("source_urls", []) or []
        clean_urls = [u for u in raw_urls if not is_placeholder_url(u)]
        removed = len(raw_urls) - len(clean_urls)
        if removed:
            logger.warning(
                "[SourcingAgent] Removed %d placeholder URL(s) from %s source_urls.",
                removed,
                startup.get("name", "unknown"),
            )
            item = dict(item)
            item["startup"] = dict(startup)
            item["startup"]["source_urls"] = clean_urls
        return item

    def _build_known_public_note(self) -> str:
        """
        Build a human-readable list of known public tickers for prompt injection.
        Example: "RXRX (Recursion Pharmaceuticals), SDGR (Schrödinger), ..."
        Known names are maintained in a lookup table; tickers without a name
        entry fall back to the ticker symbol only.
        """
        _TICKER_NAMES = {
            "RXRX": "Recursion Pharmaceuticals",
            "SDGR": "Schrödinger",
            "RLAY": "Relay Therapeutics",
            "ABCL": "AbCellera Biologics",
            "ABSI": "Absci Corporation",
            "EXAI": "Exscientia (now merged into RXRX)",
        }
        parts = []
        for ticker in self.config.example_tickers:
            name = _TICKER_NAMES.get(ticker, ticker)
            parts.append(f"{ticker} ({name})")
        return ", ".join(parts)

    def _filter_public_companies(
        self, results: List[StartupScreeningResult]
    ) -> List[StartupScreeningResult]:
        """
        Remove any result that has leaked a publicly-traded company into the
        private company list.  Two checks are applied:

        1. status == "ipo" — the LLM correctly recognised the company is public
           but failed to exclude it from the output.
        2. Name similarity — the company name contains a known public company
           name substring (case-insensitive).  This catches cases like
           'Recursion Pharmaceuticals' appearing when the LLM was asked for
           private companies only.
        """
        _TICKER_NAMES = {
            "RXRX": "Recursion Pharmaceuticals",
            "SDGR": "Schrödinger",
            "RLAY": "Relay Therapeutics",
            "ABCL": "AbCellera Biologics",
            "ABSI": "Absci Corporation",
            "EXAI": "Exscientia",
        }
        known_names_lower = {
            name.lower() for name in _TICKER_NAMES.values()
        }
        filtered, removed = [], []
        for r in results:
            name_lower = r.startup.name.lower()
            is_ipo = r.startup.status == "ipo"
            name_match = any(known in name_lower for known in known_names_lower)
            if is_ipo or name_match:
                removed.append(r.startup.name)
            else:
                filtered.append(r)
        if removed:
            logger.info(
                "[SourcingAgent] Removed %d public company/ies from private list: %s",
                len(removed),
                ", ".join(removed),
            )
        return filtered

    @staticmethod
    def _format_search_results(results: List[SearchResult]) -> str:
        """
        Render search results as a numbered list for LLM consumption.

        When results come from PrivateCompanySearchProvider the `source` field
        carries "source_type:reliability" (e.g. "press_release:medium-high"),
        which is surfaced to the LLM so it can grade evidence quality.
        """
        lines = []
        for i, r in enumerate(results, 1):
            tag = r.source.upper() if r.source else "WEB"
            line = f"{i}. [{tag}] {r.title}"
            if r.published_date:
                line += f" ({r.published_date})"
            line += f"\n   {r.snippet}"
            line += f"\n   Source: {r.url}"
            lines.append(line)
        return "\n\n".join(lines)

    @staticmethod
    def _save_screening_results(
        results: List[StartupScreeningResult], output_dir: Path
    ) -> None:
        """Save full screening results (with scores) to sourcing_screening_results.json."""
        path = output_dir / "sourcing_screening_results.json"
        data = [r.model_dump() for r in results]
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("[SourcingAgent] Screening results saved → %s", path.name)


def extract_startup_profiles(
    screening_results: List[StartupScreeningResult],
) -> List[StartupProfile]:
    """
    Utility: extract the StartupProfile from each screening result.

    Used by the orchestrator to pass a clean profile list to downstream agents
    (DiligenceAgent, ValidatorAgent) that don't need the scoring metadata.
    """
    return [r.startup for r in screening_results]
