# Industry Research Reports

This directory holds Chinese sell-side research reports (PDF) used as TIER 1 evidence
by the RAG retrieval layer (`src/retrieval/industry_research_retriever.py`).

PDFs are not committed due to copyright (reports from brokerages such as CITIC, Huatai, etc.).

Reports used in the reference run:
- 11 Chinese brokerage reports covering AI drug discovery, molecular modeling,
  and precision medicine sectors (2022–2024)

To reproduce: place PDF reports in this directory and set `USE_MOCK_PROVIDERS=false`.
The `IndustryResearchRetriever` uses PyMuPDF with GBK/UTF-8 fallback encoding for parsing.
