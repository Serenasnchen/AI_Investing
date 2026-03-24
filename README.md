# AI-Driven Investment Research Workflow

An agentic research pipeline that generates institutional-quality investment research reports for any sector. The default target is **AI Drug Discovery (AI for Pharma)**; any sector can be targeted at runtime via a single CLI argument.

Built on the [Anthropic Claude API](https://docs.anthropic.com/en/api) with a 5-agent architecture coordinated by a central orchestrator. Each run produces a complete research package: industry overview, private company memos, public market analysis, and a fully-formatted report in Markdown, HTML, Word, and PDF.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Project Structure](#3-project-structure)
4. [Environment Setup](#4-environment-setup)
5. [API Keys and Configuration](#5-api-keys-and-configuration)
6. [How to Run](#6-how-to-run)
7. [Data Sources](#7-data-sources)
8. [Outputs](#8-outputs)
9. [Reproducibility and Limitations](#9-reproducibility-and-limitations)
10. [Future Improvements](#10-future-improvements)

---

## 1. Project Overview

**Goal:** Automate the investment research workflow for a target sector, from raw signal collection to a structured, citation-backed research report — without human intervention.

**Default research sector:** AI Drug Discovery (AI for Pharma)

**Core research stages implemented:**

| Stage | Agent | What it does |
|---|---|---|
| Primary Market — Sourcing | `SourcingAgent` | Discovers private companies, scores on 5 dimensions, produces a ranked shortlist |
| Primary Market — Analyzing | `DiligenceAgent` | Writes a 10-section investment memo per top-ranked company |
| Secondary Market — Research | `PublicMarketAgent` | Analyzes listed peers, retrieves live market data, builds a catalyst calendar |
| Quality Validation | `ValidatorAgent` | Cross-checks all prior outputs across 4 quality dimensions |
| Report Synthesis | `ReportWriterAgent` | Synthesizes everything into a structured ~25,000-character research report |

**Final outputs per run:**

| Format | File | Description |
|---|---|---|
| Markdown | `final_report.md` | Primary output; all citations numbered |
| HTML | `report_v2.html` | Self-contained web report with embedded charts |
| Word | `report.docx` | For sharing and printing |
| PDF | `report_v2.pdf` | Generated via MS Word COM automation (Windows) |

---

## 2. System Architecture

The system uses a **three-layer architecture** that strictly separates data retrieval, reasoning, and workflow orchestration.

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 — PROVIDER LAYER  (src/providers/ + retrieval/) │
│  Raw data only. No reasoning. Swappable backends.        │
│                                                          │
│  SearchProvider · FinancialDataProvider                  │
│  CompanyDataProvider · PubMedProvider                    │
│  ClinicalTrialsProvider · IndustryResearchRetriever      │
│  PaperRetriever · PrivateCompanySearchProvider           │
└──────────────────────────┬──────────────────────────────┘
                           │  Typed data objects (Pydantic)
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 2 — AGENT LAYER  (src/agents/)                    │
│  Reasoning + analysis only. Injected providers.          │
│                                                          │
│  SourcingAgent → DiligenceAgent → PublicMarketAgent      │
│              → ValidatorAgent → ReportWriterAgent        │
└──────────────────────────┬──────────────────────────────┘
                           │  Pydantic models between agents
┌──────────────────────────▼──────────────────────────────┐
│  LAYER 3 — ORCHESTRATION LAYER  (src/pipelines/)         │
│  Sequence scheduling, provider injection, persistence.   │
│  ResearchOrchestrator.run() → FinalReport                │
└─────────────────────────────────────────────────────────┘
```

**Agent responsibilities:**

| Agent | Input | Output | Key design |
|---|---|---|---|
| `SourcingAgent` | Search results + industry RAG | `List[StartupScreeningResult]` with 5-dim scores | Tool-then-LLM; search backend is swappable |
| `DiligenceAgent` | Top-N from Sourcing + PubMed + ClinicalTrials + RAG | `List[CompanyDiligenceMemo]` (10 sections each) | Multi-source context injection; evidence vs. inference separation |
| `PublicMarketAgent` | YFinance quotes + ClinicalTrials pipeline data | `List[PublicCompanyProfile]` + `List[CatalystEvent]` | Valuation numbers filled directly from YFinance, never via LLM |
| `ValidatorAgent` | All prior agent outputs (JSON) | `ValidationReport` with severity-tagged issues | 4 dimensions: missing_evidence, unsupported_claim, conflict, overconfident_inference |
| `ReportWriterAgent` | All prior outputs + ValidationReport | `FinalReport` → `final_report.md` | Citations numbered post-hoc; Markdown direct output mode |

For full design details, design philosophy, and a record of key engineering challenges, see [docs/architecture.md](docs/architecture.md).
For tool evaluation criteria and alternatives analysis, see [docs/tool_selection.md](docs/tool_selection.md).

---

## 3. Project Structure

```
AI_Investing/
├── main.py                         # CLI entry point
├── requirements.txt
├── .env.example                    # Copy to .env and fill in keys
│
├── src/
│   ├── config.py                   # SectorConfig dataclass; reads all env vars
│   ├── agents/                     # 5 specialized agents + BaseAgent
│   │   ├── base_agent.py           # Anthropic API call, prompt rendering, JSON repair
│   │   ├── sourcing_agent.py
│   │   ├── diligence_agent.py
│   │   ├── public_market_agent.py
│   │   ├── validator_agent.py
│   │   └── report_writer_agent.py
│   ├── providers/                  # Data retrieval layer (Mock + Real implementations)
│   │   ├── search_provider.py
│   │   ├── private_company_search_provider.py  # DuckDuckGo / FileBackedProvider
│   │   ├── financial_data_provider.py          # YFinance
│   │   ├── company_data_provider.py            # Crunchbase stub
│   │   ├── pubmed_provider.py                  # NCBI E-utilities
│   │   └── clinical_trials_provider.py         # ClinicalTrials.gov API v2
│   ├── retrieval/                  # Local PDF RAG retrievers
│   │   ├── industry_research_retriever.py      # Sell-side research PDFs (TIER 1)
│   │   └── paper_retriever.py                  # Academic paper PDFs (TIER 2)
│   ├── reporting/                  # Output format generators
│   │   ├── html_report.py          # report.html + report_v2.html
│   │   ├── docx_report.py          # report.docx via python-docx
│   │   ├── pdf_report.py           # report_v2.pdf via xhtml2pdf or docx2pdf
│   │   ├── manual_graph_inserter.py            # Inserts graphs from data/raw/graphs/
│   │   └── industry_chart_extractor.py         # Extracts charts from research PDFs
│   ├── models/                     # Pydantic data models
│   │   ├── company.py              # PrivateCompany, PublicCompany, Catalyst, Valuation
│   │   └── report.py               # DiligenceMemo, ValidationReport, FinalReport
│   ├── pipelines/
│   │   └── orchestrator.py         # ResearchOrchestrator; wires providers → agents
│   └── visualization/
│       └── plot_sourcing.py        # Sourcing ranking bar chart (matplotlib)
│
├── prompts/                        # Prompt templates (Markdown, injected with {sector})
│   ├── sourcing.md
│   ├── diligence.md
│   ├── public_market.md
│   ├── validator.md
│   └── report_writer.md
│
├── data/
│   ├── raw/
│   │   ├── graphs/                 # Manual PNG/JPG charts — injected into HTML report
│   │   ├── papers/                 # Academic PDFs for RAG (TIER 2 evidence)
│   │   └── private_company_search.json   # File-backed fallback for private company search
│   ├── industryresearch/           # Sell-side research PDFs for RAG (TIER 1 evidence)
│   └── processed/                  # Intermediate JSON per run: {run_id}/
│
├── outputs/                        # Final report files per run: {run_id}/
│
└── docs/
    ├── architecture.md             # Design philosophy, agent details, engineering challenges
    └── tool_selection.md           # Tool evaluation criteria and alternatives analysis
```

---

## 4. Environment Setup

**Python version:** 3.8 or later (tested on 3.8 and 3.10)

```bash
# 1. Clone / enter the project
cd AI_Investing

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

**Core dependencies installed by `requirements.txt`:**

| Package | Purpose |
|---|---|
| `anthropic` | Claude API client |
| `pydantic` | Typed data models between agents |
| `python-dotenv` | Loads `.env` file |
| `yfinance` | Real-time market data |
| `duckduckgo-search` | Private company search |
| `PyMuPDF` | PDF text extraction (Chinese encoding support) |
| `pypdf` | Fallback PDF reader |
| `matplotlib` | Sourcing ranking chart |
| `markdown` | Markdown → HTML conversion |
| `curl_cffi` | HTTP transport for duckduckgo-search |

**Optional packages** (for PDF export — install separately if needed):

```bash
pip install python-docx          # Word document generation
pip install docx2pdf             # PDF via MS Word COM (Windows only)
# xhtml2pdf is attempted but may fail on Python 3.8; docx2pdf is the reliable fallback
```

---

## 5. API Keys and Configuration

**All credentials are loaded from `.env`. Never hardcode keys in source files.**

```bash
cp .env.example .env
# Open .env and fill in the required values
```

### Required

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key. Get yours at [console.anthropic.com](https://console.anthropic.com). Required for all real-LLM runs. |

### Optional — data providers

| Variable | Default | Description |
|---|---|---|
| `NCBI_API_KEY` | _(none)_ | PubMed rate limit increases from 3 req/s → 10 req/s. Get at [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/). |
| `PERPLEXITY_API_KEY` | _(none)_ | Enables `RealPerplexitySearchProvider` for higher-quality private company search. If absent, DuckDuckGo is used. |
| `CRUNCHBASE_API_KEY` | _(none)_ | Enables `RealCrunchbaseProvider` for structured company profiles. If absent, mock company data is used. |

### Optional — runtime mode flags

| Variable | Default | Effect |
|---|---|---|
| `USE_MOCK_LLM` | `false` | `true` → all agents return pre-written mock outputs; no Anthropic API call |
| `USE_MOCK_PROVIDERS` | _(same as `USE_MOCK_LLM`)_ | `true` → all providers return mock data; no external API calls |
| `USE_REAL_FINANCIAL_DATA` | `false` | `true` → use `RealYFinanceProvider` even when other providers are mocked |
| `USE_FILE_SEARCH` | `false` | `true` → use `FileBackedPrivateCompanySearchProvider` from `data/raw/private_company_search.json` |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Override the Claude model name |
| `MAX_TOKENS` | `16000` | Maximum output tokens per LLM call |

### `.env.example`

```dotenv
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Mock mode — set both true for a zero-API-call offline run
USE_MOCK_LLM=false
USE_MOCK_PROVIDERS=false

# Optional data providers
# PERPLEXITY_API_KEY=your_perplexity_key
# CRUNCHBASE_API_KEY=your_crunchbase_key
# NCBI_API_KEY=your_ncbi_key

# Optional overrides
# CLAUDE_MODEL=claude-sonnet-4-6
# MAX_TOKENS=16000
# USE_REAL_FINANCIAL_DATA=false
# USE_FILE_SEARCH=false
```

---

## 6. How to Run

### Mode 1 — Full real run (recommended for evaluation)

Requires `ANTHROPIC_API_KEY` in `.env`. Uses real Claude LLM + real YFinance data + DuckDuckGo search.

```bash
python main.py --sector "AI drug discovery"
```

With verbose logging:

```bash
python main.py --sector "AI drug discovery" --verbose
```

With custom public tickers:

```bash
python main.py --sector "AI drug discovery" --tickers RXRX SDGR RLAY ABCL ABSI
```

### Mode 2 — Real LLM + real financial data, mock search

Useful when DuckDuckGo rate-limits or when you want deterministic private company results while keeping real market data.

```bash
USE_FILE_SEARCH=true python main.py --sector "AI drug discovery"
```

Requires `data/raw/private_company_search.json` to exist (pre-cached search results).

### Mode 3 — Real LLM + real YFinance, mock everything else

```bash
USE_MOCK_PROVIDERS=true USE_REAL_FINANCIAL_DATA=true python main.py --sector "AI drug discovery"
```

Use this when you want to test LLM reasoning with real market data but avoid search API calls.

### Mode 4 — Full mock mode (offline, zero API calls, < 5 seconds)

No API keys required. Returns pre-written outputs to verify the pipeline end-to-end.

```bash
USE_MOCK_LLM=true python main.py --sector "AI drug discovery"
```

### Other sectors (no code changes needed)

```bash
python main.py --sector "autonomous vehicles" --tickers TSLA GM F
python main.py --sector "quantum computing"   --tickers IONQ RGTI IBM GOOGL
python main.py --sector "climate tech"        --tickers ENPH FSLR RUN PLUG
python main.py --sector "synthetic biology"   --tickers GINKGO AMRS BEAM
python main.py --sector "fintech AI"          --tickers UPST AFRM SQ SOFI
```

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--sector` | `"AI drug discovery"` | Research sector (injected into all agent prompts at runtime) |
| `--tickers` | `RXRX SDGR RLAY ABCL ABSI` | Space-separated public tickers for secondary market analysis |
| `--sourcing-count` | `8` | Number of private companies to surface |
| `--diligence-count` | `3` | Number of private companies to deep-dive |
| `--verbose` / `-v` | off | Enable DEBUG logging |

---

## 7. Data Sources

| Source | Type | Used by | Notes |
|---|---|---|---|
| **DuckDuckGo Search** | Live web search | `SourcingAgent` | Free, no key. Rate-limits under high frequency; `FileBackedProvider` fallback is automatic |
| **Yahoo Finance (yfinance)** | Real-time market data | `PublicMarketAgent` | Free, no key. ~15-min delayed quotes. Covers NYSE/NASDAQ |
| **ClinicalTrials.gov API v2** | Clinical trial registry | `DiligenceAgent`, `PublicMarketAgent` | Free, no key. Used to verify NCT IDs and pipeline stages |
| **PubMed E-utilities (NCBI)** | Academic literature | `DiligenceAgent`, `ReportWriterAgent` | Free; 3 req/s without key, 10 req/s with `NCBI_API_KEY` |
| **Local industry research PDFs** | Sell-side research reports | All agents (TIER 1) | Place PDFs in `data/industryresearch/`. PyMuPDF + GBK-fallback encoding |
| **Local academic papers** | Research papers | `DiligenceAgent`, `ReportWriterAgent` | Place PDFs in `data/raw/papers/`. UTF-8 encoding |
| **File-backed private search** | Pre-cached search JSON | `SourcingAgent` (fallback) | `data/raw/private_company_search.json`; activated by `USE_FILE_SEARCH=true` or automatically on DuckDuckGo failure |
| **Manual graphs** | PNG/JPG chart images | HTML report | Place images in `data/raw/graphs/`. Filename keywords map to report sections |

**Evidence priority hierarchy used by LLM agents:**

```
TIER 1 (highest)  →  Industry research PDFs (IndustryResearchRetriever)
TIER 2            →  PubMed abstracts + ClinicalTrials registry data
TIER 3 (lowest)   →  DuckDuckGo search results + LLM parametric knowledge
```

---

## 8. Outputs

Each run creates a timestamped directory: `outputs/{run_id}/` where `run_id = YYYYMMDD_HHMMSS`.

```
outputs/20260324_131524/
├── final_report.md          # Full investment research report (~25,000 chars, 8 sections)
├── report_v2.html           # Self-contained web report; all images base64-embedded
├── report.html              # Simplified HTML version
├── report.docx              # Word document with embedded charts
├── report_v2.pdf            # PDF (generated via MS Word COM on Windows)
├── memos.md                 # Combined investment memos from DiligenceAgent
├── public_market.md         # Public market analysis from PublicMarketAgent
├── charts/
│   └── sourcing_ranking.png # Bar chart: top private companies by score
└── industry_charts/         # Charts extracted from industry research PDFs
    └── *.png
```

Intermediate JSON files (per run) are saved in `data/processed/{run_id}/`:

```
data/processed/20260324_131524/
├── sourcing_screening_results.json   # StartupScreeningResult[] with scores
├── startup_profiles.json             # StartupProfile[] (plain, no scores)
├── company_memos.json                # CompanyDiligenceMemo[]
├── public_market_profiles.json       # PublicCompanyProfile[]
├── catalysts.json                    # CatalystEvent[]
└── validation_report.json            # ValidationReport
```

---

## 9. Reproducibility and Limitations

**What varies between runs:**

- `final_report.md` content will differ between runs because it depends on live API responses (DuckDuckGo, YFinance, PubMed, ClinicalTrials.gov) and the LLM's stochastic output.
- YFinance prices and company news are real-time; public market figures in the report reflect the state at execution time.
- DuckDuckGo search results vary by time and may trigger rate limits. The pipeline automatically falls back to `FileBackedPrivateCompanySearchProvider`; if `data/raw/private_company_search.json` does not exist, the agent will still run but with reduced private company evidence.

**Known limitations:**

1. **DuckDuckGo rate limits.** High-frequency calls (>10 req/min) fail ~30% of the time. The fallback mechanism mitigates this but does not eliminate it. For production use, replace with Perplexity or Brave Search.

2. **No real Crunchbase integration.** `RealCrunchbaseProvider` is stubbed; the interface exists but requires a paid Crunchbase API key and a complete implementation. Without it, the system uses `MockCompanyDataProvider`.

3. **PDF export is Windows-only.** `report_v2.pdf` is generated via `docx2pdf` which uses MS Word COM automation. On macOS/Linux, the PDF step is skipped; the `.docx` file is still produced.

4. **LLM outputs are non-deterministic.** Report content, scoring rationale, and company rankings can differ between runs even for the same sector. For reproducible outputs, use `USE_MOCK_LLM=true`.

5. **Private company data is limited.** DuckDuckGo provides general web search results, not structured company databases. Funding figures, team sizes, and recent financials may be incomplete or outdated. This is a fundamental limitation of free search APIs and is the primary motivation for the industry RAG tier.

6. **This system is a research assistant, not an investment decision engine.** All outputs are for analytical and educational purposes. The report represents automated synthesis of publicly available information and should not be treated as financial advice or a basis for investment decisions.

---

## 10. Future Improvements

1. **Stable private company data source.** Replace DuckDuckGo with a structured database (Pitchbook API, LinkedIn scraper, or a curated startup database). The `PrivateCompanySearchProvider` interface is ready; only the implementation needs to be swapped.

2. **SEC EDGAR integration.** Add a `SECFilingsProvider` to pull 10-K/10-Q filings for public companies, enabling financial model construction beyond the summary metrics currently retrieved from YFinance.

3. **Parallel agent execution.** `DiligenceAgent` currently processes each company sequentially. Since memos are independent, they can be executed in parallel (e.g., `asyncio` + `ThreadPoolExecutor`), reducing total pipeline latency by up to 60%.

4. **Interactive web interface.** Wrap the orchestrator in a FastAPI backend with a React front end, allowing users to configure sector, tickers, and parameters through a browser rather than the CLI.

5. **Agent memory and iterative refinement.** Allow `ReportWriterAgent` to request specific follow-up searches from `SourcingAgent` or `DiligenceAgent` when evidence is insufficient, implementing a multi-turn research loop rather than a single-pass pipeline.

6. **Broader sector coverage with pre-configured profiles.** Add a `sectors/` directory with per-sector YAML configurations (default tickers, key terminology, relevant regulatory bodies), enabling one-click setup for common sectors without CLI parameter tuning.
