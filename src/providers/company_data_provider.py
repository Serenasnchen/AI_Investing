"""
CompanyDataProvider: interface for company intelligence databases.

Intended real integrations:
  - Crunchbase API   (company profiles, funding rounds, investors)
  - PitchBook API    (private market data, valuations, cap tables)
  - LinkedIn API     (team / headcount data)

The agent layer never imports a concrete implementation directly;
it receives a CompanyDataProvider instance injected by the orchestrator.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FundingRound:
    round_type: str           # "Series A", "Series B", etc.
    amount_usd_m: Optional[float]
    date: Optional[str]
    lead_investors: List[str] = field(default_factory=list)


@dataclass
class CompanyProfile:
    """Structured company intelligence from a data provider."""
    name: str
    description: str
    founded_year: Optional[int] = None
    hq: Optional[str] = None
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    employee_count: Optional[int] = None
    total_funding_usd_m: Optional[float] = None
    stage: Optional[str] = None
    key_investors: List[str] = field(default_factory=list)
    funding_rounds: List[FundingRound] = field(default_factory=list)
    recent_news_headlines: List[str] = field(default_factory=list)
    website: Optional[str] = None


class CompanyDataProvider(ABC):
    """Abstract interface for company intelligence APIs."""

    @abstractmethod
    def get_company_profile(self, company_name: str) -> Optional[CompanyProfile]:
        """
        Retrieve a structured company profile by name.

        Returns None if the company is not found in the data source.
        """
        ...

    @abstractmethod
    def search_companies(self, sector: str, stage: Optional[str] = None) -> List[CompanyProfile]:
        """
        Search for companies in a given sector, optionally filtered by stage.

        Returns a list of matching CompanyProfile objects.
        """
        ...


class RealCrunchbaseProvider(CompanyDataProvider):
    """
    Production implementation using the Crunchbase Basic API.

    To activate:
      1. Set CRUNCHBASE_API_KEY in your .env file.
      2. pip install requests
      3. Replace the NotImplementedError bodies below with real API calls.

    API docs: https://data.crunchbase.com/docs/using-the-api
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_company_profile(self, company_name: str) -> Optional[CompanyProfile]:
        raise NotImplementedError(
            "RealCrunchbaseProvider is not yet implemented. "
            "Set USE_MOCK_PROVIDERS=true or implement the Crunchbase API call here."
        )

    def search_companies(self, sector: str, stage: Optional[str] = None) -> List[CompanyProfile]:
        raise NotImplementedError(
            "RealCrunchbaseProvider.search_companies is not yet implemented."
        )
