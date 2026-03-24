"""
MockCompanyDataProvider: returns pre-written company profiles for known AI pharma tickers.

Simulates what Crunchbase / PitchBook would return for public company lookups.
Used by PublicMarketAgent to enrich market data with company context.
"""
import logging
from typing import Dict, List, Optional

from .company_data_provider import CompanyDataProvider, CompanyProfile, FundingRound

logger = logging.getLogger(__name__)

_PROFILES: Dict[str, CompanyProfile] = {
    "RXRX": CompanyProfile(
        name="Recursion Pharmaceuticals",
        description=(
            "Recursion Pharmaceuticals operates the Recursion OS — an industrial-scale AI platform "
            "combining high-content cellular phenomics imaging with biological foundation models. "
            "The company generates petabytes of biological data annually and uses it to train "
            "Phenom-Beta, a foundation model for cell biology. Its January 2025 merger with Exscientia "
            "added generative chemistry and automated synthesis capabilities, creating the most "
            "integrated AI drug-discovery platform among public companies."
        ),
        founded_year=2013,
        hq="Salt Lake City, UT, USA",
        sector="Biotechnology",
        sub_sector="AI Drug Discovery",
        employee_count=850,
        total_funding_usd_m=850.0,
        stage="Public",
        key_investors=["NVIDIA", "SoftBank Vision Fund 2", "Baillie Gifford", "Bristol Myers Squibb"],
        funding_rounds=[
            FundingRound("Series D", 436.0, "2021-02", ["SoftBank"]),
            FundingRound("Strategic", 50.0, "2023-07", ["NVIDIA"]),
        ],
        recent_news_headlines=[
            "Recursion completes merger with Exscientia, creating integrated AI drug-discovery platform (Jan 2025)",
            "REC-994 Phase II trial in cerebral cavernous malformation on track for H2 2025 readout",
            "NVIDIA deepens partnership with additional $50M equity investment and DGX Cloud access",
            "Roche collaboration expanded to include three new oncology phenomics screening campaigns",
        ],
        website="https://www.recursion.com",
    ),
    "SDGR": CompanyProfile(
        name="Schrödinger",
        description=(
            "Schrödinger offers a physics-based computational platform for drug discovery and materials "
            "science. Its FEP+ (free energy perturbation) technology is widely regarded as the gold "
            "standard for predicting binding affinity in small-molecule design. The company licenses its "
            "software to 15 of the top 20 pharmaceutical companies and also operates a proprietary "
            "pipeline. Revenue is split ~70% SaaS / 30% drug pipeline milestones."
        ),
        founded_year=1990,
        hq="New York, NY, USA",
        sector="Biotechnology / Software",
        sub_sector="Physics-based Drug Design",
        employee_count=760,
        total_funding_usd_m=580.0,
        stage="Public",
        key_investors=["Bill & Melinda Gates Foundation", "D.E. Shaw", "Newview Capital"],
        recent_news_headlines=[
            "FY2024 software revenue grows 18% YoY to $160M; enterprise renewal rate exceeds 90%",
            "New FEP+ partnership signed with Merck for kinase selectivity programme",
            "SGR-1505 (MCL-1 inhibitor) Phase I dose escalation complete; recommended Phase II dose announced Q1 2025",
            "Schrödinger launches AI-enhanced FEP+ model with improved accuracy on challenging targets",
        ],
        website="https://www.schrodinger.com",
    ),
    "ABCL": CompanyProfile(
        name="AbCellera Biologics",
        description=(
            "AbCellera uses microfluidics, single-cell sequencing, and AI to discover therapeutic "
            "antibodies at ultra-high throughput. Its platform can screen billions of B cells and "
            "identify optimal antibody sequences in days rather than months. The company became "
            "prominent during COVID-19 for discovering bamlanivimab (with Eli Lilly), which generated "
            "significant royalty revenue. Post-COVID, it is transitioning to next-gen oncology and "
            "immunology antibody programmes."
        ),
        founded_year=2012,
        hq="Vancouver, BC, Canada",
        sector="Biotechnology",
        sub_sector="AI Antibody Discovery",
        employee_count=680,
        total_funding_usd_m=740.0,
        stage="Public",
        key_investors=["Eli Lilly", "AstraZeneca", "Pfizer", "GV (Google Ventures)"],
        recent_news_headlines=[
            "COVID-19 antibody royalties decline 65% YoY; company accelerates non-COVID pipeline",
            "New AstraZeneca partnership for bispecific antibody discovery in oncology signed",
            "AbCellera launches dedicated oncology subsidiary with $150M internal funding commitment",
            "Cash balance of $720M provides multi-year runway; management evaluating M&A opportunities",
        ],
        website="https://www.abcellera.com",
    ),
    "RLAY": CompanyProfile(
        name="Relay Therapeutics",
        description=(
            "Relay Therapeutics uses its Dynamo platform — combining molecular dynamics simulations, "
            "cryo-EM structural biology, and machine learning — to drug previously undruggable protein "
            "conformations. The company focuses on kinases and other dynamic proteins where traditional "
            "structure-based drug design has failed. Lead programme RLY-2608 is a mutant-selective "
            "PI3Ka inhibitor in Phase II for breast cancer, with a potential best-in-class tolerability "
            "profile versus current standard of care alpelisib."
        ),
        founded_year=2016,
        hq="Cambridge, MA, USA",
        sector="Biotechnology",
        sub_sector="Computational Drug Design",
        employee_count=290,
        total_funding_usd_m=700.0,
        stage="Public",
        key_investors=["GV (Google Ventures)", "Redmile Group", "Boxer Capital", "Roche"],
        recent_news_headlines=[
            "RLY-2608 OPERA Phase II trial fully enrolled; interim data expected Q3 2025",
            "Roche collaboration for RLY-5836 programme progressing; $30M milestone payment received",
            "Relay presents Dynamo platform data at AACR demonstrating superiority of conformation-selective design",
            "Cash runway extended to 2027 following $250M equity offering at $8.50/share",
        ],
        website="https://www.relaytx.com",
    ),
    "ABSI": CompanyProfile(
        name="Absci Corporation",
        description=(
            "Absci's Integrated Drug Creation platform combines generative AI for antibody sequence "
            "design with cell-free synthetic biology for rapid protein expression and testing. The "
            "company can design, build, and screen thousands of de-novo antibody variants in weeks. "
            "In 2024, Absci achieved what it calls the first IND-enabling studies for a fully "
            "AI-de-novo-designed antibody — a claimed first in the industry."
        ),
        founded_year=2011,
        hq="Portland, OR, USA",
        sector="Biotechnology",
        sub_sector="Generative AI Antibody Design",
        employee_count=220,
        total_funding_usd_m=380.0,
        stage="Public",
        key_investors=["AstraZeneca", "GV (Google Ventures)", "Redmile Group"],
        recent_news_headlines=[
            "Absci achieves IND-enabling milestone for first fully AI-de-novo-designed antibody (Oct 2024)",
            "AstraZeneca bispecific antibody partnership initiates second programme",
            "Absci presents de-novo antibody design data at ASH; demonstrates antigen-binding from scratch",
            "Cash runway of 18 months; management evaluating strategic financing options",
        ],
        website="https://www.absci.com",
    ),
    "EXAI": CompanyProfile(
        name="Exscientia (merged into Recursion / RXRX)",
        description=(
            "Exscientia was an Oxford-based AI drug design company that produced the first AI-designed "
            "molecule to enter clinical trials (DSP-1181, OCD, 2020). The company built automated "
            "synthesis robots and generative chemistry models. It merged with Recursion Pharmaceuticals "
            "in January 2025 and is no longer independently listed."
        ),
        founded_year=2012,
        hq="Oxford, UK (now part of Recursion)",
        sector="Biotechnology",
        sub_sector="AI Drug Design",
        stage="Merged / Acquired",
        recent_news_headlines=[
            "Exscientia merger with Recursion Pharmaceuticals completed January 2025; now trades as RXRX",
        ],
        website="https://www.recursion.com",
    ),
}


class MockCompanyDataProvider(CompanyDataProvider):
    """
    Mock company data provider for development / course demos.

    Returns pre-written profiles for major AI drug discovery public companies.
    Falls back to a generic profile for unknown tickers.
    """

    def get_company_profile(self, company_name: str) -> Optional[CompanyProfile]:
        # Try exact match first, then case-insensitive ticker match
        result = _PROFILES.get(company_name.upper())
        if result is None:
            for profile in _PROFILES.values():
                if company_name.lower() in profile.name.lower():
                    result = profile
                    break
        if result:
            logger.info("[MockCompanyDataProvider] Found profile for %r.", company_name)
        else:
            logger.warning("[MockCompanyDataProvider] No profile for %r — returning None.", company_name)
        return result

    def search_companies(self, sector: str, stage: Optional[str] = None) -> List[CompanyProfile]:
        results = list(_PROFILES.values())
        if stage:
            results = [p for p in results if p.stage and stage.lower() in p.stage.lower()]
        logger.info("[MockCompanyDataProvider] search sector=%r stage=%r → %d results.", sector, stage, len(results))
        return results
