"""
PublicMarketAgent: analyzes listed companies and upcoming catalysts in the sector.

Input:  FinancialDataProvider + CompanyDataProvider (via constructor injection)
Output: (List[PublicCompanyProfile], List[CatalystEvent])
        outputs/{run_id}/public_market.md   (human-readable analysis)

Two-step pipeline:
  1. TOOL LAYER  — fetch quotes, news, and company profiles from providers
  2. AGENT LAYER — LLM produces structured profiles + catalyst calendar

Catalyst events use a standardised 5-category taxonomy:
  clinical | partnership | platform_validation | financial | regulatory
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.models.company import CatalystEvent, PublicCompanyProfile, ValuationMetrics
from src.providers.financial_data_provider import FinancialDataProvider
from src.providers.company_data_provider import CompanyDataProvider
from src.providers.clinical_trials_provider import (
    ClinicalTrialsProvider,
    COMPANY_DRUG_MAP,
)
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Category display labels for the markdown table
_CATEGORY_LABEL = {
    "clinical": "Clinical",
    "partnership": "Partnership",
    "platform_validation": "Platform",
    "financial": "Financial",
    "regulatory": "Regulatory",
}


class PublicMarketAgent(BaseAgent):
    """
    Responsibilities:
    - Retrieve structured market data (quotes, news) via FinancialDataProvider
    - Retrieve company background and context via CompanyDataProvider
    - Populate ValuationMetrics directly from provider data (no hallucination)
    - Use LLM to produce business classification, positioning, bull/bear cases,
      analyst conviction, and a standardised catalyst calendar
    - Save human-readable Markdown to outputs/{run_id}/public_market.md
    """

    prompt_file = "public_market.md"

    def __init__(
        self,
        config,
        financial_provider: FinancialDataProvider,
        company_provider: CompanyDataProvider,
        clinical_trials_provider=None,
    ):
        super().__init__(config)
        self.financial_provider = financial_provider
        self.company_provider = company_provider
        self.clinical_trials_provider = clinical_trials_provider

    def run(
        self,
        output_dir: Optional[Path] = None,
    ) -> Tuple[List[PublicCompanyProfile], List[CatalystEvent]]:
        # ── Step 1: Tool layer — fetch structured data for all tickers ────────
        market_context, valuation_map, quote_map = self._fetch_market_data()

        if not market_context.strip():
            logger.warning(
                "[PublicMarketAgent] No market data fetched — falling back to LLM-only mode."
            )
            market_context = f"No structured data available for sector: {self.config.sector}"

        # ── Step 1b: ClinicalTrials.gov — pipeline / catalyst verification ────
        clinical_trials_text = self._fetch_clinical_trials_for_tickers()

        # ── Step 2: Agent layer — LLM analysis + catalyst extraction ──────────
        prompt = self._render_prompt(
            structured_market_data=market_context,
            clinical_trials_data=clinical_trials_text,
        )
        raw = self._call_llm(
            user_prompt=prompt,
            system_prompt=(
                "You are a buy-side equity analyst. "
                "Return your answer ONLY as a valid JSON object with two keys: "
                "'companies' (array) and 'catalysts' (array). No prose, no markdown fences."
            ),
        )

        try:
            data = self._parse_json(raw)
            companies = []
            for c in data.get("companies", []):
                ticker = c.get("ticker", "")
                # Merge provider-sourced ValuationMetrics (prevents hallucinated ratios)
                if ticker in valuation_map:
                    c["valuation_metrics"] = valuation_map[ticker].model_dump()
                # Overwrite market cap, price, name, exchange with real provider values
                if ticker in quote_map:
                    q = quote_map[ticker]
                    if q.market_cap_usd_b:
                        c["market_cap_usd_b"] = q.market_cap_usd_b
                    if q.name:
                        c["name"] = q.name
                    if q.exchange:
                        c["exchange"] = q.exchange
                companies.append(PublicCompanyProfile(**c))

            catalysts = [CatalystEvent(**cat) for cat in data.get("catalysts", [])]

            logger.info(
                "[PublicMarketAgent] %d companies, %d catalysts.",
                len(companies),
                len(catalysts),
            )

            if output_dir is not None and companies:
                self._save_markdown(companies, catalysts, output_dir)

            return companies, catalysts

        except Exception as exc:
            logger.error("[PublicMarketAgent] Failed to parse LLM response: %s", exc)
            return [], []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_clinical_trials_for_tickers(self) -> str:
        """
        Fetch verified clinical trial data for all configured tickers.

        Queries COMPANY_DRUG_MAP for each ticker/company name, deduplicates
        by NCT ID, and formats a combined text block for the prompt.

        Returns a "no verified data" notice if no provider is configured or
        no trials are found.
        """
        provider = self.clinical_trials_provider
        if provider is None:
            return (
                "## ClinicalTrials.gov Data\n\n"
                "ClinicalTrialsProvider not configured. "
                "Do NOT infer phase, timing, or enrollment status."
            )

        seen_ncts: set = set()
        all_studies: list = []

        # Look up known drugs for each ticker (by ticker symbol and company name)
        lookup_keys = list(self.config.example_tickers)
        for ticker in self.config.example_tickers:
            # Also try the full company name if stored in COMPANY_DRUG_MAP
            for key in COMPANY_DRUG_MAP:
                if key.upper() == ticker.upper() and key not in lookup_keys:
                    lookup_keys.append(key)

        for key in lookup_keys:
            drugs = COMPANY_DRUG_MAP.get(key, [])
            if drugs:
                for drug in drugs:
                    for s in provider.get_drug_trials(drug, max_results=3):
                        if s.nct_id not in seen_ncts:
                            seen_ncts.add(s.nct_id)
                            all_studies.append(s)
            else:
                # Empty drug list means "search by name"
                for s in provider.search_studies(key, max_results=2):
                    if s.nct_id not in seen_ncts:
                        seen_ncts.add(s.nct_id)
                        all_studies.append(s)

        logger.info(
            "[PublicMarketAgent] ClinicalTrials for %d ticker(s): %d verified trial(s).",
            len(self.config.example_tickers),
            len(all_studies),
        )
        return provider.format_for_llm(
            all_studies,
            label="ClinicalTrials.gov — Public Company Pipeline Data",
        )

    def _is_mock_provider(self) -> bool:
        """Return True if the financial provider is a mock (not real market data)."""
        return "mock" in type(self.financial_provider).__name__.lower()

    def _fetch_market_data(self):
        """
        Fetch market data for all configured tickers.

        Returns:
            (market_context_str: str,
             valuation_map: dict[ticker -> ValuationMetrics],
             quote_map: dict[ticker -> StockQuote])
        """
        sections = []
        valuation_map = {}
        quote_map = {}

        for ticker in self.config.example_tickers:
            quote = self.financial_provider.get_quote(ticker)
            news = self.financial_provider.get_news(ticker, num_items=3)
            profile = self.company_provider.get_company_profile(ticker)

            if quote is None and profile is None:
                logger.debug(
                    "[PublicMarketAgent] No data for ticker %s — skipping.", ticker
                )
                continue

            entry = {"ticker": ticker}
            if quote:
                entry["market_data"] = {
                    "name": quote.name,
                    "exchange": quote.exchange,
                    "price_usd": quote.price,
                    "market_cap_usd_b": quote.market_cap_usd_b,
                    "ev_revenue_ratio": quote.ev_revenue_ratio,
                    "price_to_sales": quote.price_to_sales,
                    "pe_ratio": quote.pe_ratio,
                    "week_52_high": quote.week_52_high,
                    "week_52_low": quote.week_52_low,
                    "ytd_change_pct": quote.ytd_change_pct,
                    "cash_usd_b": quote.cash_usd_b,
                }
                # Build a provider-sourced ValuationMetrics object
                valuation_map[ticker] = ValuationMetrics(
                    ev_revenue_ratio=quote.ev_revenue_ratio,
                    price_to_sales=quote.price_to_sales,
                    pe_ratio=quote.pe_ratio,
                    cash_usd_b=quote.cash_usd_b,
                    week_52_high=quote.week_52_high,
                    week_52_low=quote.week_52_low,
                    ytd_change_pct=quote.ytd_change_pct,
                )
                quote_map[ticker] = quote
            if profile:
                entry["company_profile"] = {
                    "description": profile.description,
                    "founded_year": profile.founded_year,
                    "hq": profile.hq,
                    "employee_count": profile.employee_count,
                    "key_investors": profile.key_investors,
                    "sub_sector": profile.sub_sector,
                }
            if news:
                entry["recent_news"] = [
                    {"headline": n.headline, "date": n.date, "summary": n.summary}
                    for n in news
                ]
            sections.append(entry)

        logger.info(
            "[PublicMarketAgent] Assembled market data for %d tickers.", len(sections)
        )
        data_date = datetime.now().strftime("%Y-%m-%d")
        is_mock = self._is_mock_provider()
        if is_mock:
            source_line = "// [MOCK DATA — omit data source in final report output]"
        else:
            source_line = f"// [数据来源：Yahoo Finance（截至{data_date}）— 在报告中引用市场数据时必须标注此来源]"
        market_context = source_line + "\n" + json.dumps(sections, indent=2, ensure_ascii=False)
        return market_context, valuation_map, quote_map

    # ------------------------------------------------------------------
    # Markdown renderer
    # ------------------------------------------------------------------

    def _save_markdown(
        self,
        companies: List[PublicCompanyProfile],
        catalysts: List[CatalystEvent],
        output_dir: Path,
    ) -> None:
        """Save the full public market analysis as public_market.md."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "public_market.md"

        lines = [
            "# Public Market Analysis",
            f"*Sector: {self.config.sector}  |  "
            f"{len(companies)} companies  |  {len(catalysts)} catalysts*",
            f"*Market data retrieved: {datetime.now().strftime('%Y-%m-%d')}*",
            "",
            "---",
            "",
        ]

        # ── Sector snapshot table ─────────────────────────────────────────
        lines += [
            "## Sector Snapshot",
            "",
            "| Ticker | Name | Mkt Cap | Type | EV/Rev | YTD | Conviction |",
            "|--------|------|---------|------|--------|-----|------------|",
        ]
        data_date = datetime.now().strftime("%Y-%m-%d")
        for c in companies:
            vm = c.valuation_metrics
            ev_rev = f"{vm.ev_revenue_ratio:.1f}x" if vm and vm.ev_revenue_ratio else "N/A"
            ytd = (
                f"{vm.ytd_change_pct * 100:+.0f}%"
                if vm and vm.ytd_change_pct is not None
                else "N/A"
            )
            mkt_cap = f"${c.market_cap_usd_b:.1f}B" if c.market_cap_usd_b else "N/A"
            conviction = (c.analyst_conviction or "N/A").upper()
            lines.append(
                f"| {c.ticker} | {c.name} | {mkt_cap} | "
                f"{c.business_type or 'N/A'} | {ev_rev} | {ytd} | {conviction} |"
            )
        lines.append("")
        if not self._is_mock_provider():
            lines.append(
                f"*数据来源：Yahoo Finance（截至{data_date}）。"
                "市价为延迟报价，仅供参考，不构成投资建议。*"
            )
        lines.append("")

        # ── Company profiles ──────────────────────────────────────────────
        lines += ["---", "", "## Company Profiles", ""]
        for c in companies:
            lines += _render_company_md(c)
            lines.append("")

        # ── Catalyst calendar table ───────────────────────────────────────
        lines += [
            "---",
            "",
            "## Catalyst Calendar",
            "",
            "| # | Ticker | Category | Event summary | Timing | Probability | Impact |",
            "|---|--------|----------|---------------|--------|-------------|--------|",
        ]
        for i, cat in enumerate(catalysts, 1):
            cat_label = _CATEGORY_LABEL.get(cat.category, cat.category)
            timing = cat.timing or cat.expected_date or "TBD"
            prob = cat.probability or "N/A"
            impact = cat.expected_impact or "N/A"
            desc_short = (cat.description or "")[:60] + (
                "…" if (cat.description or "") and len(cat.description) > 60 else ""
            )
            lines.append(
                f"| {i} | {cat.ticker or cat.company_name} | {cat_label} | "
                f"{desc_short} | {timing} | {prob} | {impact} |"
            )
        lines.append("")

        # ── Catalyst detail sections ──────────────────────────────────────
        lines += ["---", "", "## Catalyst Details", ""]
        for i, cat in enumerate(catalysts, 1):
            lines += _render_catalyst_md(i, cat)
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(
            "[PublicMarketAgent] Saved public market analysis → %s", path.name
        )


# ── Module-level markdown helpers ─────────────────────────────────────────────

def _render_company_md(c: PublicCompanyProfile) -> List[str]:
    lines = []
    mkt_cap = f"${c.market_cap_usd_b:.1f}B" if c.market_cap_usd_b else "N/A"
    conviction = (c.analyst_conviction or "N/A").upper()

    lines.append(f"### {c.ticker} — {c.name}")
    lines.append(
        f"**Market Cap:** {mkt_cap}  |  **Exchange:** {c.exchange or 'N/A'}  |  "
        f"**Type:** {c.business_type or 'N/A'}"
    )
    if c.value_chain_position:
        lines.append(f"**Value Chain Position:** {c.value_chain_position}")
    if c.technology_approach:
        lines.append(f"**Technology:** {c.technology_approach}")
    lines.append("")

    # Valuation block
    vm = c.valuation_metrics
    if vm:
        val_parts = []
        if vm.ev_revenue_ratio is not None:
            val_parts.append(f"EV/Rev: {vm.ev_revenue_ratio:.1f}x")
        if vm.price_to_sales is not None:
            val_parts.append(f"P/S: {vm.price_to_sales:.1f}x")
        if vm.cash_usd_b is not None:
            val_parts.append(f"Cash: ${vm.cash_usd_b:.2f}B")
        if vm.ytd_change_pct is not None:
            val_parts.append(f"YTD: {vm.ytd_change_pct * 100:+.0f}%")
        if vm.week_52_low is not None and vm.week_52_high is not None:
            val_parts.append(f"52w: ${vm.week_52_low:.2f}–${vm.week_52_high:.2f}")
        if val_parts:
            lines.append("**Valuation:** " + "  |  ".join(val_parts))
    if c.valuation_commentary:
        lines.append(c.valuation_commentary)
    lines.append("")

    if c.recent_developments:
        lines.append("**Recent Developments:**")
        lines.append(c.recent_developments)
        lines.append("")

    if c.bull_cases:
        lines.append("**Bull Cases:**")
        for bc in c.bull_cases:
            lines.append(f"- {bc}")
        lines.append("")

    if c.bear_cases:
        lines.append("**Bear Cases:**")
        for bc in c.bear_cases:
            lines.append(f"- {bc}")
        lines.append("")

    lines.append(f"**Analyst Conviction: {conviction}**")
    if c.conviction_rationale:
        lines.append(f"*{c.conviction_rationale}*")

    return lines


def _render_catalyst_md(index: int, cat: CatalystEvent) -> List[str]:
    lines = []
    cat_label = _CATEGORY_LABEL.get(cat.category, cat.category)
    timing = cat.timing or cat.expected_date or "TBD"

    lines.append(
        f"### [{index}] {cat.ticker or cat.company_name} — "
        f"{cat.description or cat.category}"
    )
    meta = [f"**Category:** {cat_label}", f"**Timing:** {timing}"]
    if cat.probability:
        meta.append(f"**Probability:** {cat.probability}")
    if cat.expected_impact:
        meta.append(f"**Expected Impact:** {cat.expected_impact}")
    lines.append("  |  ".join(meta))
    lines.append("")

    if cat.description:
        lines.append(cat.description)
        lines.append("")

    if cat.bull_case:
        lines.append(f"**Bull Case:** {cat.bull_case}")
    if cat.bear_case:
        lines.append(f"**Bear Case:** {cat.bear_case}")
    if cat.evidence:
        lines.append(f"*Evidence: {cat.evidence}*")

    return lines
