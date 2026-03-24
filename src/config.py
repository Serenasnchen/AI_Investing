"""
Configuration loader: reads environment variables and holds sector-level settings.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_RAW_DIR = ROOT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = ROOT_DIR / "data" / "processed"
OUTPUTS_DIR = ROOT_DIR / "outputs"


@dataclass
class SectorConfig:
    """All sector-specific parameters injected into agent prompts."""

    sector: str
    # Example public tickers relevant to the sector — override per sector.
    example_tickers: List[str] = field(
        default_factory=lambda: ["RXRX", "SDGR", "RLAY", "ABCL", "ABSI"]
    )
    # Number of private companies the sourcing agent should surface.
    sourcing_target_count: int = 8
    # Number of private companies to deep-dive in diligence.
    diligence_target_count: int = 3

    @property
    def use_mock_llm(self) -> bool:
        return os.getenv("USE_MOCK_LLM", "false").lower() == "true"

    @property
    def use_mock_providers(self) -> bool:
        # Defaults to the same value as use_mock_llm so a single flag controls both.
        # Set USE_MOCK_PROVIDERS=false independently to mix real data with mock LLM.
        return os.getenv("USE_MOCK_PROVIDERS", str(self.use_mock_llm)).lower() == "true"

    @property
    def use_real_financial_data(self) -> bool:
        """
        When True, use RealYFinanceProvider for market data regardless of
        use_mock_providers.  This allows running with mock search/LLM but
        real market data (useful for demos and development).

        Set USE_REAL_FINANCIAL_DATA=true to activate.
        Automatically True when use_mock_providers is False.
        """
        if not self.use_mock_providers:
            return True
        return os.getenv("USE_REAL_FINANCIAL_DATA", "false").lower() == "true"

    @property
    def anthropic_api_key(self) -> str:
        if self.use_mock_llm:
            return "mock-key"  # never sent to the API
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Copy .env.example → .env and add your key, "
                "or set USE_MOCK_LLM=true to run without an API key."
            )
        return key

    @property
    def model(self) -> str:
        return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    @property
    def max_tokens(self) -> int:
        return int(os.getenv("MAX_TOKENS", "16000"))
