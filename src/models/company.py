"""
Pydantic data models for companies and market events.

Naming convention:
  StartupProfile         — a private (pre-IPO) company identified during sourcing
  DimensionScore         — one dimension in the 5-axis pre-screening scorecard
  StartupScreeningResult — full sourcing output: StartupProfile + scoring + classification
  PublicCompanyProfile   — a listed company analyzed by the public market agent
  CatalystEvent          — an upcoming market-moving event for a listed company
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class StartupProfile(BaseModel):
    """
    Output unit of SourcingAgent.
    Represents one private company candidate surfaced from search results.
    """
    name: str
    founded_year: Optional[int] = None
    hq: Optional[str] = Field(None, description="City, Country")
    stage: Optional[str] = Field(
        None, description="Funding stage: Seed | Series A | Series B | Late Stage"
    )
    total_funding_usd_m: Optional[float] = Field(
        None, description="Cumulative funding raised in $M USD"
    )
    technology_approach: Optional[str] = Field(
        None, description="1-2 sentence description of core AI / technology approach"
    )
    technology_category: Optional[str] = Field(
        None,
        description=(
            "High-level technology bucket: e.g. 'generative chemistry', "
            "'protein design', 'phenomics', 'multiomics'"
        ),
    )
    key_investors: List[str] = Field(default_factory=list)
    summary: Optional[str] = Field(
        None, description="2-3 sentence company overview derived from search results"
    )
    status: str = Field(
        default="active",
        description="Company operational status: active | acquired | merged | ipo",
    )
    source_urls: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Backward-compatible alias so any code that imports PrivateCompany still works
# ---------------------------------------------------------------------------
PrivateCompany = StartupProfile


class DimensionScore(BaseModel):
    """One axis of the 5-dimension pre-screening scorecard."""

    score: float = Field(description="Score on a 1.0–5.0 scale (5 = strongest signal)")
    rationale: str = Field(description="One sentence justifying the score")


class StartupScreeningResult(BaseModel):
    """
    Full output unit of the enhanced SourcingAgent.

    Wraps a StartupProfile with investment pre-screening metadata:
    classification, evidence citations, 5-dimension scores, and a priority rank.
    """

    startup: StartupProfile
    classification: str = Field(
        description=(
            "Technology bucket: generative_chemistry | protein_design | phenomics | "
            "multiomics | antibody_design | cro_platform | saas_tools | other"
        )
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Up to 3 verbatim evidence snippets from search results (with source URL)",
    )
    dimension_scores: Dict[str, DimensionScore] = Field(
        default_factory=dict,
        description=(
            "Scores across 5 axes: tech_frontier, commercialization_potential, "
            "data_flywheel, team_credibility, information_completeness. "
            "Each value is a DimensionScore object."
        ),
    )
    total_score: float = Field(
        default=0.0,
        description="Sum of all dimension scores (max 25.0 = 5 dimensions × 5.0)",
    )
    score_rationale: str = Field(
        default="",
        description=(
            "2–3 sentence overall rationale: why this company ranks where it does "
            "and the single most important risk or uncertainty."
        ),
    )
    priority_rank: int = Field(
        default=0,
        description="1-based rank by total_score within the current sourcing run",
    )


class ValuationMetrics(BaseModel):
    """
    Structured valuation metrics populated directly from FinancialDataProvider.
    All fields are optional — null when not reported (e.g. pre-revenue companies).
    """

    ev_revenue_ratio: Optional[float] = Field(
        None, description="Enterprise Value / trailing-12-month Revenue"
    )
    price_to_sales: Optional[float] = Field(
        None, description="Price-to-Sales (market cap / annual revenue)"
    )
    pe_ratio: Optional[float] = Field(
        None, description="Price-to-Earnings; null for unprofitable companies"
    )
    cash_usd_b: Optional[float] = Field(
        None, description="Cash and equivalents in $B USD"
    )
    week_52_high: Optional[float] = Field(None, description="52-week high price (USD)")
    week_52_low: Optional[float] = Field(None, description="52-week low price (USD)")
    ytd_change_pct: Optional[float] = Field(
        None, description="Year-to-date price change as a decimal (e.g. -0.42 = -42%)"
    )


class PublicCompanyProfile(BaseModel):
    """
    Output unit of PublicMarketAgent (companies array).
    Represents one listed company with market data and structured analyst commentary.
    """

    # ── Identifiers ───────────────────────────────────────────────────────────
    name: str
    ticker: str
    exchange: Optional[str] = Field(None, description="e.g. NASDAQ, NYSE")
    market_cap_usd_b: Optional[float] = Field(None, description="Market cap in $B USD")

    # ── Business classification ───────────────────────────────────────────────
    business_type: Optional[str] = Field(
        None,
        description=(
            "Company model in AI drug discovery: "
            "'platform' (tool/software only) | 'pipeline' (own drugs) | "
            "'hybrid' (platform + pipeline) | 'saas' (recurring software) | "
            "'cro' (contract research services)"
        ),
    )
    value_chain_position: Optional[str] = Field(
        None,
        description=(
            "Where in the AI drug discovery value chain: "
            "e.g. 'target ID + hit generation (phenomics)', "
            "'lead optimisation (generative chemistry)', "
            "'antibody discovery (AI-assisted B-cell screening)', "
            "'protein structure simulation (physics + ML)'"
        ),
    )
    technology_approach: Optional[str] = Field(
        None, description="1-2 sentence core technology / platform description"
    )

    # ── Market data ───────────────────────────────────────────────────────────
    valuation_metrics: Optional[ValuationMetrics] = Field(
        None,
        description="Structured valuation metrics populated from FinancialDataProvider",
    )
    valuation_commentary: Optional[str] = Field(
        None,
        description=(
            "Narrative: current multiple vs. peers; cheap / fair / expensive assessment "
            "anchored to the provided market data and peer comparison"
        ),
    )
    recent_developments: Optional[str] = Field(
        None, description="2-3 most significant news items in the past 6-12 months"
    )

    # ── Analyst view ──────────────────────────────────────────────────────────
    bull_cases: List[str] = Field(
        default_factory=list,
        description=(
            "1-3 specific bull cases grounded in mechanism, customer structure, "
            "or pipeline — not generic statements"
        ),
    )
    bear_cases: List[str] = Field(
        default_factory=list,
        description=(
            "1-3 specific bear cases grounded in cash, clinical, or business model risk"
        ),
    )
    analyst_conviction: Optional[str] = Field(
        None, description="Analyst conviction level: 'high' | 'medium' | 'low'"
    )
    conviction_rationale: Optional[str] = Field(
        None,
        description=(
            "1-sentence rationale for the conviction level, naming the specific "
            "factor that drives it"
        ),
    )
    source_urls: List[str] = Field(default_factory=list)


# Backward-compatible alias
PublicCompany = PublicCompanyProfile


class CatalystEvent(BaseModel):
    """
    Output unit of PublicMarketAgent (catalysts array).
    Represents one upcoming market-moving event with standardised category,
    timing, probability, expected impact, and directional bull/bear scenarios.
    """

    company_name: str
    ticker: Optional[str] = None

    # ── Standardised category (NEW — replaces free-text catalyst_type) ────────
    category: str = Field(
        description=(
            "Standardised event category: "
            "'clinical' (trial readout / FDA decision / IND filing) | "
            "'partnership' (deal announcement / licensing) | "
            "'platform_validation' (technology milestone / publication) | "
            "'financial' (earnings / guidance / capital raise) | "
            "'regulatory' (label expansion / approval / hold)"
        )
    )

    # ── Event description ─────────────────────────────────────────────────────
    timing: Optional[str] = Field(
        None,
        description=(
            "When the event is expected: 'Q3 2025', 'H2 2025', 'next 6-12 months', "
            "or a specific date — as precise as the evidence allows"
        ),
    )
    description: Optional[str] = Field(
        None,
        description=(
            "Specific event description grounded in the available data: "
            "name the drug, trial, or deal — not a generic statement"
        ),
    )

    # ── Probability and impact ────────────────────────────────────────────────
    probability: Optional[str] = Field(
        None,
        description=(
            "Analyst probability estimate: 'high' | 'medium' | 'low' "
            "or a decimal (e.g. '0.65' for 65%)"
        ),
    )
    expected_impact: Optional[str] = Field(
        None,
        description=(
            "Stock move estimate on the positive outcome: "
            "e.g. '+40-60%' or 'high' — anchor to historical precedents where possible"
        ),
    )

    # ── Directional scenarios ─────────────────────────────────────────────────
    bull_case: Optional[str] = Field(
        None,
        description=(
            "Upside scenario directly tied to this specific event: "
            "what happens and estimated % stock move on positive outcome"
        ),
    )
    bear_case: Optional[str] = Field(
        None,
        description=(
            "Downside scenario directly tied to this specific event: "
            "what happens and estimated % stock move on negative outcome"
        ),
    )

    # ── Evidence ──────────────────────────────────────────────────────────────
    evidence: Optional[str] = Field(
        None,
        description=(
            "Source of the catalyst claim: news headline, press release, "
            "clinical trial registration, or earnings guidance"
        ),
    )

    # ── Legacy fields kept for backward compatibility ─────────────────────────
    catalyst_type: Optional[str] = Field(
        None,
        description=(
            "[Legacy] Free-text event type. "
            "Prefer the standardised 'category' field for new analyses."
        ),
    )
    expected_date: Optional[str] = Field(
        None,
        description="[Legacy] Expected date string. Prefer 'timing' for new analyses.",
    )
    potential_impact: Optional[str] = Field(
        None,
        description=(
            "[Legacy] Combined bull/bear impact string. "
            "Prefer 'bull_case' / 'bear_case' / 'expected_impact' for new analyses."
        ),
    )


# Backward-compatible alias
Catalyst = CatalystEvent
