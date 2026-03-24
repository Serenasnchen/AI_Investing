"""
MockFinancialDataProvider: returns pre-written stock quotes and news for AI pharma tickers.

Simulates what Yahoo Finance / Alpha Vantage would return.
All prices and figures are illustrative — not real-time market data.
"""
import logging
from typing import Dict, List, Optional

from .financial_data_provider import FinancialDataProvider, StockQuote, NewsItem

logger = logging.getLogger(__name__)

_QUOTES: Dict[str, StockQuote] = {
    "RXRX": StockQuote(
        ticker="RXRX",
        name="Recursion Pharmaceuticals",
        exchange="NASDAQ",
        price=4.85,
        market_cap_usd_b=2.8,
        pe_ratio=None,           # pre-revenue / negative earnings
        ev_revenue_ratio=7.8,
        price_to_sales=7.2,
        week_52_high=11.20,
        week_52_low=3.42,
        ytd_change_pct=-0.42,
        cash_usd_b=0.52,
    ),
    "SDGR": StockQuote(
        ticker="SDGR",
        name="Schrödinger Inc.",
        exchange="NASDAQ",
        price=22.40,
        market_cap_usd_b=3.1,
        pe_ratio=None,
        ev_revenue_ratio=14.8,
        price_to_sales=14.2,
        week_52_high=26.80,
        week_52_low=16.50,
        ytd_change_pct=0.08,
        cash_usd_b=0.85,
    ),
    "ABCL": StockQuote(
        ticker="ABCL",
        name="AbCellera Biologics",
        exchange="NASDAQ",
        price=2.95,
        market_cap_usd_b=1.4,
        pe_ratio=None,
        ev_revenue_ratio=4.2,
        price_to_sales=5.8,
        week_52_high=5.10,
        week_52_low=2.30,
        ytd_change_pct=-0.22,
        cash_usd_b=0.72,
    ),
    "RLAY": StockQuote(
        ticker="RLAY",
        name="Relay Therapeutics",
        exchange="NASDAQ",
        price=8.15,
        market_cap_usd_b=0.9,
        pe_ratio=None,
        ev_revenue_ratio=None,   # pure pipeline, no product revenue
        price_to_sales=None,
        week_52_high=14.60,
        week_52_low=5.80,
        ytd_change_pct=-0.35,
        cash_usd_b=0.60,
    ),
    "ABSI": StockQuote(
        ticker="ABSI",
        name="Absci Corporation",
        exchange="NASDAQ",
        price=3.80,
        market_cap_usd_b=0.7,
        pe_ratio=None,
        ev_revenue_ratio=11.5,
        price_to_sales=10.8,
        week_52_high=5.20,
        week_52_low=2.90,
        ytd_change_pct=0.03,
        cash_usd_b=0.18,
    ),
    "EXAI": StockQuote(  # legacy — merged into RXRX
        ticker="EXAI",
        name="Exscientia (merged into Recursion / RXRX)",
        exchange="NASDAQ",
        price=0.0,
        market_cap_usd_b=0.0,
        ytd_change_pct=None,
        cash_usd_b=None,
    ),
}

_NEWS: Dict[str, List[NewsItem]] = {
    "RXRX": [
        NewsItem(
            headline="Recursion completes Exscientia merger, unveils combined Recursion OS platform",
            date="2025-01-14",
            source="PR Newswire",
            summary="The combined company integrates Exscientia's generative chemistry and automated synthesis with Recursion's phenomics imaging and Phenom-Beta foundation model.",
        ),
        NewsItem(
            headline="REC-994 Phase II interim analysis expected H2 2025; CCM endpoint validation underway",
            date="2025-02-20",
            source="Recursion Investor Relations",
            summary="Recursion confirms Phase II trial in cerebral cavernous malformation remains on schedule. Primary endpoint: reduction in lesion burden at 6 months vs. placebo.",
        ),
        NewsItem(
            headline="NVIDIA and Recursion expand DGX Cloud agreement for Phenom-Beta model training",
            date="2024-11-05",
            source="NVIDIA Newsroom",
            summary="Agreement provides Recursion with preferential access to NVIDIA's latest Blackwell GPU infrastructure for next-generation biological foundation model development.",
        ),
    ],
    "SDGR": [
        NewsItem(
            headline="Schrödinger Q4 2024 software revenue $42M, full year +18% YoY",
            date="2025-02-12",
            source="Schrödinger Investor Relations",
            summary="FY2024 total software revenue $160M, enterprise renewals >90%. FY2025 guidance: $180-190M software revenue. Pipeline milestone revenue $28M from Lilly programme.",
        ),
        NewsItem(
            headline="SGR-1505 Phase I complete; recommended Phase II dose 200mg QD in haematologic malignancies",
            date="2025-01-28",
            source="ASCO Rapid Communication",
            summary="The MCL-1 inhibitor SGR-1505 showed a manageable safety profile at the recommended dose with early signals of anti-tumour activity in AML and DLBCL.",
        ),
        NewsItem(
            headline="Schrödinger and Merck sign multi-year FEP+ agreement for kinase selectivity programmes",
            date="2024-10-15",
            source="BusinessWire",
            summary="Multi-year enterprise agreement expands Schrödinger's presence at Merck Research Labs across oncology and cardiovascular disease programmes.",
        ),
    ],
    "ABCL": [
        NewsItem(
            headline="AbCellera Q3 2024: COVID royalties fall 65%; partnership pipeline refilling",
            date="2024-11-08",
            source="AbCellera Investor Relations",
            summary="Revenue of $18M in Q3, down from $52M a year ago primarily from COVID antibody royalty decline. New partnerships with AstraZeneca and Pfizer announced for non-COVID programmes.",
        ),
        NewsItem(
            headline="AbCellera launches dedicated oncology antibody subsidiary with $150M commitment",
            date="2024-09-20",
            source="GlobeNewswire",
            summary="The new oncology-focused entity will use the AbCellera discovery platform for bispecific and ADC antibody generation, with IND targets in 2026.",
        ),
        NewsItem(
            headline="AbCellera cash balance $720M; management evaluating strategic acquisitions",
            date="2025-01-10",
            source="Bloomberg",
            summary="CEO Carl Hansen signals intent to deploy capital into accretive M&A in the antibody discovery and engineering space as COVID royalty revenue normalises.",
        ),
    ],
    "RLAY": [
        NewsItem(
            headline="Relay Therapeutics OPERA trial fully enrolled; RLY-2608 Phase II data Q3 2025",
            date="2025-01-22",
            source="Relay Investor Relations",
            summary="The Phase II OPERA trial of RLY-2608 in PI3Ka-mutant breast cancer is fully enrolled. Top-line ORR data versus alpelisib control arm expected in Q3 2025.",
        ),
        NewsItem(
            headline="Roche pays $30M milestone for RLY-5836 programme progression to IND",
            date="2024-12-03",
            source="Reuters",
            summary="The milestone payment from Roche for the collaborative RLY-5836 oncology programme reaching IND-filing milestone extends Relay's cash runway.",
        ),
        NewsItem(
            headline="Relay presents Dynamo platform data at AACR 2024: MD + cryo-EM + ML outperforms static structure design",
            date="2024-04-16",
            source="AACR Annual Meeting",
            summary="Academic and industry attendees cited Relay's comparative analysis as one of the strongest demonstrations of conformation-selective drug design advantage over traditional SBDD.",
        ),
    ],
    "ABSI": [
        NewsItem(
            headline="Absci achieves IND-enabling milestone for first fully AI-de-novo-designed antibody",
            date="2024-10-08",
            source="Absci Corporation",
            summary="The undisclosed oncology target antibody — designed entirely from scratch using Absci's generative AI without any template antibody — completed all required preclinical safety studies.",
        ),
        NewsItem(
            headline="AstraZeneca initiates second bispecific antibody programme with Absci's Integrated Drug Creation platform",
            date="2024-12-19",
            source="AstraZeneca Media Centre",
            summary="The second collaborative programme targets a validated tumour microenvironment mechanism; Absci receives $15M upfront with up to $200M in milestones.",
        ),
        NewsItem(
            headline="Absci presents de-novo antibody design results at ASH 2024; demonstrates zero-shot antigen binding",
            date="2024-12-09",
            source="American Society of Hematology",
            summary="Data shows Absci's generative model can design functional antibody sequences against novel haematology targets without any training examples for that specific antigen.",
        ),
    ],
    "EXAI": [
        NewsItem(
            headline="Exscientia merged with Recursion Pharmaceuticals; no longer independently traded",
            date="2025-01-14",
            source="PR Newswire",
            summary="Exscientia shareholders received 0.7055 shares of RXRX per EXAI share. The combined company continues under the Recursion name and ticker.",
        ),
    ],
}


class MockFinancialDataProvider(FinancialDataProvider):
    """
    Mock financial data provider for development / course demos.

    Returns pre-written quotes and news for major AI drug discovery public companies.
    """

    source_note = "Mock data (illustrative, not real-time)"

    def get_quote(self, ticker: str) -> Optional[StockQuote]:
        quote = _QUOTES.get(ticker.upper())
        if quote:
            logger.info("[MockFinancialDataProvider] Quote for %s: $%.2f, mktcap $%.1fB.",
                        ticker, quote.price, quote.market_cap_usd_b)
        else:
            logger.warning("[MockFinancialDataProvider] No quote for ticker %r.", ticker)
        return quote

    def get_news(self, ticker: str, num_items: int = 5) -> List[NewsItem]:
        news = _NEWS.get(ticker.upper(), [])
        result = news[:num_items]
        logger.info("[MockFinancialDataProvider] News for %s: %d items.", ticker, len(result))
        return result
