"""
ResearchOrchestrator: sequences all 5 agents and persists intermediate data.

Three-layer architecture:
  TOOL LAYER        src/providers/    raw data retrieval (search, market data, company info)
  AGENT LAYER       src/agents/       reasoning, analysis, structured Pydantic output
  ORCHESTRATION     this file         sequencing, provider injection, persistence

Per-run output layout:
  data/processed/{run_id}/
    startup_profiles.json        ← SourcingAgent output
    company_memos.json           ← DiligenceAgent output
    public_market_profiles.json  ← PublicMarketAgent output (companies)
    catalysts.json               ← PublicMarketAgent output (catalysts)
    validation_report.json       ← ValidatorAgent output

  outputs/{run_id}/
    final_report.md              ← ReportWriterAgent output
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union

from src.config import SectorConfig, DATA_PROCESSED_DIR, OUTPUTS_DIR, DATA_RAW_DIR
from src.retrieval import PaperRetriever
from src.retrieval.industry_research_retriever import IndustryResearchRetriever
from src.agents import (
    SourcingAgent,
    DiligenceAgent,
    PublicMarketAgent,
    ValidatorAgent,
    ReportWriterAgent,
)
from src.agents.sourcing_agent import extract_startup_profiles
from src.models.report import FinalReport

logger = logging.getLogger(__name__)


def _build_private_search_provider(config: SectorConfig):
    """
    Factory: return a PrivateCompanySearchProvider for private company research.

    Selection logic:
      1. Mock mode (USE_MOCK_LLM=true or USE_MOCK_PROVIDERS=true)
         → MockPrivateCompanySearchProvider (no network calls)

      2. File-backed override (USE_FILE_SEARCH=true or data/raw/private_company_search.json exists)
         → FileBackedPrivateCompanySearchProvider
         Useful when pre-collected search results are available.

      3. Real mode default
         → DuckDuckGoPrivateCompanySearchProvider (free, no API key)
         Falls back gracefully if duckduckgo-search is not installed.
    """
    import os
    from src.providers.private_company_search_provider import (
        MockPrivateCompanySearchProvider,
        DuckDuckGoPrivateCompanySearchProvider,
        FileBackedPrivateCompanySearchProvider,
    )

    if config.use_mock_providers:
        logger.info("PrivateSearch: MockPrivateCompanySearchProvider (mock mode)")
        return MockPrivateCompanySearchProvider()

    # File-backed override: set USE_FILE_SEARCH=true or place the JSON file
    file_path = DATA_RAW_DIR / "private_company_search.json"
    if os.getenv("USE_FILE_SEARCH", "false").lower() == "true" or file_path.exists():
        logger.info("PrivateSearch: FileBackedPrivateCompanySearchProvider ← %s", file_path.name)
        return FileBackedPrivateCompanySearchProvider(file_path)

    # Default: DuckDuckGo (gracefully degrades to mock if library not installed)
    try:
        import duckduckgo_search  # noqa: F401  — just check it's importable
        logger.info("PrivateSearch: DuckDuckGoPrivateCompanySearchProvider")
        return DuckDuckGoPrivateCompanySearchProvider()
    except ImportError:
        logger.warning(
            "duckduckgo-search not installed; falling back to FileBackedProvider. "
            "Run: pip install duckduckgo-search"
        )
        return FileBackedPrivateCompanySearchProvider(file_path)


def _build_industry_retriever(config: SectorConfig):
    """
    Factory: 返回 IndustryResearchRetriever 实例。

    从 data/industryresearch/ 目录加载所有 PDF 研报。
    如果目录为空或不存在，返回空检索器（不抛异常，pipeline 继续运行）。
    """
    from src.config import DATA_RAW_DIR
    industry_dir = DATA_RAW_DIR.parent / "industryresearch"
    retriever = IndustryResearchRetriever(directory=industry_dir)
    if retriever.is_empty:
        logger.warning(
            "IndustryResearchRetriever: 无研报 — "
            "将研报 PDF 放入 data/industryresearch/ 以启用最高优先级行业证据。"
        )
    else:
        logger.info(
            "IndustryResearchRetriever: %d chunks 就绪，来自 data/industryresearch/。",
            len(retriever._chunks),
        )
    return retriever


def _build_pubmed_provider(config: SectorConfig):
    """
    Factory: return a PubMedProvider for academic literature retrieval.

    Selection logic:
      1. Mock mode (USE_MOCK_LLM=true or USE_MOCK_PROVIDERS=true)
         → MockPubMedProvider (no network calls, pre-populated abstracts)

      2. Real mode default
         → PubMedProvider (live NCBI E-utilities API, no auth required)
         Optional: set NCBI_API_KEY in .env for higher rate limits.
    """
    from src.providers.pubmed_provider import PubMedProvider, MockPubMedProvider

    if config.use_mock_providers:
        logger.info("PubMed: MockPubMedProvider (mock mode)")
        return MockPubMedProvider()

    logger.info("PubMed: PubMedProvider (live NCBI E-utilities API)")
    return PubMedProvider()


def _build_clinical_trials_provider(config: SectorConfig):
    """
    Factory: return a ClinicalTrialsProvider for pipeline verification.

    Selection logic:
      1. Mock mode (USE_MOCK_LLM=true or USE_MOCK_PROVIDERS=true)
         → MockClinicalTrialsProvider (no network calls, pre-populated data)

      2. Real mode default
         → ClinicalTrialsProvider (live ClinicalTrials.gov API v2, no auth needed)
    """
    from src.providers.clinical_trials_provider import (
        ClinicalTrialsProvider,
        MockClinicalTrialsProvider,
    )

    if config.use_mock_providers:
        logger.info("ClinicalTrials: MockClinicalTrialsProvider (mock mode)")
        return MockClinicalTrialsProvider()

    logger.info("ClinicalTrials: ClinicalTrialsProvider (live ClinicalTrials.gov API)")
    return ClinicalTrialsProvider()


def _build_providers(config: SectorConfig):
    """
    Factory: return (search, financial, company) provider instances.

    Four modes are supported:
      1. Full mock (USE_MOCK_PROVIDERS=true, default when USE_MOCK_LLM=true)
         No external calls; suitable for offline dev and CI.

      2. Mixed — real financial data only (USE_REAL_FINANCIAL_DATA=true)
         Uses RealYFinanceProvider for market data; keeps mock search and
         company providers.  No API keys needed beyond yfinance (free).
         Activate with: USE_MOCK_LLM=true USE_REAL_FINANCIAL_DATA=true

      3. Full real (USE_MOCK_PROVIDERS=false + API keys present)
         All three providers use live APIs.
         Requires: PERPLEXITY_API_KEY and CRUNCHBASE_API_KEY in .env.

      4. Graceful degradation (USE_MOCK_PROVIDERS=false but keys missing)
         Falls back to MockSearchProvider / MockCompanyDataProvider with a
         warning.  Allows USE_MOCK_LLM=false USE_REAL_FINANCIAL_DATA=true
         to work without Perplexity/Crunchbase keys — real LLM + real
         market data + mock search scaffolding.
    """
    import os
    from src.providers import (
        MockSearchProvider,
        MockFinancialDataProvider,
        MockCompanyDataProvider,
        RealYFinanceProvider,
    )

    # ── Financial data provider ───────────────────────────────────────────
    if config.use_real_financial_data:
        financial_provider = RealYFinanceProvider()
    else:
        financial_provider = MockFinancialDataProvider()

    # ── Search + company providers ────────────────────────────────────────
    if config.use_mock_providers:
        return (
            MockSearchProvider(),
            financial_provider,
            MockCompanyDataProvider(),
        )

    # Real mode: use live APIs only if keys are present; otherwise degrade gracefully
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    crunchbase_key = os.getenv("CRUNCHBASE_API_KEY")

    if perplexity_key and crunchbase_key:
        from src.providers import RealPerplexitySearchProvider, RealCrunchbaseProvider
        logger.info("Search: RealPerplexitySearchProvider | Company: RealCrunchbaseProvider")
        return (
            RealPerplexitySearchProvider(api_key=perplexity_key),
            financial_provider,
            RealCrunchbaseProvider(api_key=crunchbase_key),
        )

    # Graceful degradation: log which keys are missing and fall back to mocks
    missing = []
    if not perplexity_key:
        missing.append("PERPLEXITY_API_KEY")
    if not crunchbase_key:
        missing.append("CRUNCHBASE_API_KEY")
    logger.warning(
        "Missing API key(s): %s — falling back to Mock search/company providers. "
        "Set these in .env for full real-data mode.",
        ", ".join(missing),
    )
    return (
        MockSearchProvider(),
        financial_provider,
        MockCompanyDataProvider(),
    )


class ResearchOrchestrator:
    def __init__(self, config: SectorConfig):
        self.config = config

        # Build provider layer
        search_provider, financial_provider, company_provider = _build_providers(config)
        logger.info(
            "Providers: %s | %s | %s",
            type(search_provider).__name__,
            type(financial_provider).__name__,
            type(company_provider).__name__,
        )

        # Build private company search provider
        private_search_provider = _build_private_search_provider(config)

        # Build clinical trials provider
        clinical_trials_provider = _build_clinical_trials_provider(config)

        # Build PubMed provider
        pubmed_provider = _build_pubmed_provider(config)

        # Build industry research retriever (loads from data/industryresearch/)
        industry_retriever = _build_industry_retriever(config)

        # Build paper retriever (loads from data/raw/papers/ at startup)
        paper_retriever = PaperRetriever()
        if paper_retriever.is_empty:
            logger.warning(
                "PaperRetriever: no chunks loaded — "
                "place PDF files in data/raw/papers/ for academic evidence."
            )
        else:
            logger.info(
                "PaperRetriever: %d chunks ready from data/raw/papers/.",
                len(paper_retriever._chunks),
            )

        # Build agent layer with injected providers
        self.sourcing = SourcingAgent(
            config,
            search_provider=search_provider,
            private_search_provider=private_search_provider,
        )
        self.diligence = DiligenceAgent(
            config,
            private_search_provider=private_search_provider,
            paper_retriever=paper_retriever,
            clinical_trials_provider=clinical_trials_provider,
            pubmed_provider=pubmed_provider,
            industry_retriever=industry_retriever,
        )
        self.public_market = PublicMarketAgent(
            config,
            financial_provider=financial_provider,
            company_provider=company_provider,
            clinical_trials_provider=clinical_trials_provider,
        )
        self.validator = ValidatorAgent(config)
        self.report_writer = ReportWriterAgent(
            config,
            paper_retriever=paper_retriever,
            pubmed_provider=pubmed_provider,
            industry_retriever=industry_retriever,
        )

    def run(self) -> FinalReport:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create per-run output directories
        processed_dir = DATA_PROCESSED_DIR / run_id
        output_dir = OUTPUTS_DIR / run_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=== Research pipeline started | sector: %s | run: %s ===",
                    self.config.sector, run_id)
        logger.info("Intermediate data → %s", processed_dir)
        logger.info("Final report      → %s/final_report.md", output_dir)

        # ── Step 1: Sourcing ─────────────────────────────────────────────────
        logger.info("[1/5] SourcingAgent  (search → LLM classify, score & rank)")
        screening_results = self.sourcing.run(output_dir=processed_dir)
        if not screening_results:
            raise RuntimeError("SourcingAgent returned no companies. Aborting pipeline.")

        # Full screening results (with scores) already saved by SourcingAgent.run()
        # Extract plain StartupProfile list for downstream agents
        startups = extract_startup_profiles(screening_results)
        _save_json(processed_dir / "startup_profiles.json",
                   [s.model_dump() for s in startups])

        top3 = screening_results[:3]
        logger.info("[1/5] Top 3 after scoring:")
        for r in top3:
            logger.info(
                "      #%d  %-30s  total=%.1f/25.0  class=%s",
                r.priority_rank,
                r.startup.name,
                r.total_score,
                r.classification,
            )

        # ── Step 1 chart: sourcing ranking bar chart ──────────────────────
        try:
            from src.visualization.plot_sourcing import plot_sourcing_ranking
            plot_sourcing_ranking(
                screening_results_path=processed_dir / "sourcing_screening_results.json",
                output_dir=output_dir,
            )
        except Exception as exc:
            logger.warning("[1/5] Chart generation skipped: %s", exc)

        # ── Step 2: Diligence ────────────────────────────────────────────────
        logger.info(
            "[2/5] DiligenceAgent (full investment memos for top %d companies)",
            self.config.diligence_target_count,
        )
        memos = self.diligence.run(screening_results, output_dir=output_dir)
        _save_json(processed_dir / "company_memos.json",
                   [m.model_dump() for m in memos])
        logger.info(
            "[2/5] Memos complete: %s",
            " | ".join(
                f"{m.startup.name} ({m.overall_conviction})" for m in memos
            ),
        )

        # ── Step 3: Public Market ────────────────────────────────────────────
        logger.info("[3/5] PublicMarketAgent (market data → LLM analysis)")
        public_companies, catalysts = self.public_market.run(output_dir=output_dir)
        logger.info(
            "[3/5] Public market complete: %d companies, %d catalysts",
            len(public_companies),
            len(catalysts),
        )
        _save_json(processed_dir / "public_market_profiles.json",
                   [c.model_dump() for c in public_companies])
        _save_json(processed_dir / "catalysts.json",
                   [cat.model_dump() for cat in catalysts])

        # ── Step 4: Validation ───────────────────────────────────────────────
        logger.info("[4/5] ValidatorAgent (missing_evidence | unsupported_claim | conflict | overconfident_inference)")
        validation_report = self.validator.run(memos, public_companies, catalysts)
        _save_json(processed_dir / "validation_report.json",
                   validation_report.model_dump())

        # ── Step 5: Report Writing ───────────────────────────────────────────
        logger.info("[5/5] ReportWriterAgent (synthesis → final_report.md)")
        from src.providers.financial_data_provider import RealYFinanceProvider
        _is_real_yf = isinstance(self.public_market.financial_provider, RealYFinanceProvider)
        _run_date = f"{run_id[:4]}-{run_id[4:6]}-{run_id[6:8]}"
        _market_note = f"Yahoo Finance（截至{_run_date}）" if _is_real_yf else None
        final_report = self.report_writer.run(
            memos, public_companies, catalysts, validation_report,
            output_dir=output_dir,
            market_data_note=_market_note,
        )

        # ── Step 5.5: Industry chart extraction ──────────────────────────────
        try:
            from src.reporting.industry_chart_extractor import extract_industry_charts
            from src.config import ROOT_DIR
            pdf_dir = ROOT_DIR / "data" / "industryresearch"
            if pdf_dir.exists():
                extract_industry_charts(pdf_dir=pdf_dir, output_dir=output_dir)
                logger.info("[5.5] Industry charts → %s/industry_charts/", output_dir)
            else:
                logger.info("[5.5] data/industryresearch/ not found — skipping chart extraction")
        except Exception as exc:
            logger.warning("[5.5] Industry chart extraction skipped: %s", exc)

        # ── Step 6: HTML Export ──────────────────────────────────────────────
        html_v2_path = None
        try:
            from src.reporting.html_report import generate_html_report, generate_html_report_v2
            html_path = generate_html_report(output_dir)
            logger.info("[6/6] HTML report     → %s", html_path)
            html_v2_path = generate_html_report_v2(output_dir, processed_dir=processed_dir)
            logger.info("[6/6] HTML report v2  → %s", html_v2_path)
        except Exception as exc:
            logger.warning("[6/6] HTML report generation skipped: %s", exc)

        # ── Step 7: Word export ───────────────────────────────────────────────
        docx_path = None
        try:
            from src.reporting.docx_report import generate_docx_report
            docx_path = generate_docx_report(output_dir)
            logger.info("[7/8] Word report     → %s", docx_path)
        except Exception as exc:
            logger.warning("[7/8] Word export skipped: %s", exc)

        # ── Step 8: PDF export ────────────────────────────────────────────────
        try:
            from src.reporting.pdf_report import generate_pdf_report
            pdf_path = generate_pdf_report(
                output_dir,
                html_path=html_v2_path,
                docx_path=docx_path,
            )
            if pdf_path:
                logger.info("[8/8] PDF report      → %s", pdf_path)
            else:
                logger.warning("[8/8] PDF export failed (see warnings above).")
        except Exception as exc:
            logger.warning("[8/8] PDF export skipped: %s", exc)

        logger.info("=== Pipeline complete ===")
        logger.info("Intermediate files: %s/", processed_dir)
        logger.info("Final report:       %s/final_report.md", output_dir)
        logger.info("HTML report:        %s/report.html", output_dir)
        return final_report


def _save_json(path: Path, data: Union[dict, list]) -> None:
    """Write JSON to disk with UTF-8 encoding and 2-space indent."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug("Saved → %s", path.name)
