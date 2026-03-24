"""
DiligenceAgent: produces full investment memos for top-ranked private companies.

Input:  List[StartupScreeningResult]  — top N from SourcingAgent (carries evidence)
Output: List[CompanyDiligenceMemo]    — one memo per company
        outputs/{run_id}/memos.md     — combined Markdown memo document

Each memo covers 10 structured sections:
  Team, Technology, Moat, Pipeline, Business Model, Competitive Landscape,
  Bull Case, Bear Case / Risks, Overall Conviction, Evidence vs Inference

Evidence from the sourcing step is passed to the LLM so it can anchor claims
to real sources rather than hallucinating. The agent explicitly separates
evidence (cited facts) from inference (analyst judgement).
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

from src.config import SectorConfig
from src.models.company import StartupScreeningResult
from src.models.report import CompanyDiligenceMemo
from src.providers.private_company_search_provider import (
    PrivateCompanySearchProvider,
    PrivateCompanySearchResult,
    format_search_results_for_llm,
)
from src.retrieval.paper_retriever import PaperRetriever
from src.retrieval.industry_research_retriever import IndustryResearchRetriever
from src.providers.clinical_trials_provider import (
    ClinicalTrialsProvider,
    MockClinicalTrialsProvider,
    COMPANY_DRUG_MAP,
)
from src.providers.pubmed_provider import PubMedProvider
from .base_agent import BaseAgent, is_placeholder_url

logger = logging.getLogger(__name__)


class DiligenceAgent(BaseAgent):
    """
    For each company in the top-N shortlist:
      1. Serialize its StartupProfile + sourcing evidence as context
      2. Call LLM for full investment memo (10 structured sections)
      3. Inject the original StartupProfile into the parsed result
      4. Return a typed CompanyDiligenceMemo
      5. Save combined memo Markdown to outputs/{run_id}/memos.md
    """

    prompt_file = "diligence.md"

    def __init__(
        self,
        config,
        private_search_provider: Optional[PrivateCompanySearchProvider] = None,
        paper_retriever: Optional[PaperRetriever] = None,
        clinical_trials_provider=None,
        pubmed_provider=None,
        industry_retriever: Optional[IndustryResearchRetriever] = None,
    ):
        super().__init__(config)
        self.private_search_provider = private_search_provider
        self.paper_retriever = paper_retriever
        self.clinical_trials_provider = clinical_trials_provider
        self.pubmed_provider = pubmed_provider
        self.industry_retriever = industry_retriever

    def run(
        self,
        screening_results: List[StartupScreeningResult],
        output_dir: Optional[Path] = None,
    ) -> List[CompanyDiligenceMemo]:
        """
        Args:
            screening_results: sorted list from SourcingAgent — top N companies
                               with evidence snippets and score rationale
            output_dir: run-specific outputs/ directory; if provided, saves
                        memos.md there

        Returns:
            List[CompanyDiligenceMemo] — one memo per company, in rank order
        """
        memos: List[CompanyDiligenceMemo] = []
        top_n = screening_results[: self.config.diligence_target_count]

        for sr in top_n:
            memo = self._analyze_one(sr)
            if memo is not None:
                memos.append(memo)

        if output_dir is not None and memos:
            self._save_markdown(memos, output_dir)

        return memos

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _analyze_one(
        self, sr: StartupScreeningResult
    ) -> Optional[CompanyDiligenceMemo]:
        """Run one LLM call for a single company; return memo or None on failure."""
        startup = sr.startup

        # ── Step 0: Pre-search — fetch real web evidence for this company ────
        web_results: List[PrivateCompanySearchResult] = []
        if self.private_search_provider is not None:
            web_results = self.private_search_provider.search_company(
                startup.name, num_results=6
            )
            logger.info(
                "[DiligenceAgent] Pre-search '%s' → %d web results (%d high/medium-high).",
                startup.name,
                len(web_results),
                sum(1 for r in web_results if r.reliability in ("high", "medium-high")),
            )

        web_evidence_text = format_search_results_for_llm(
            web_results,
            header=f"Real-time web evidence for {startup.name}",
        )

        # Determine evidence sufficiency and build note for the LLM
        evidence_sufficiency_note = self._build_evidence_sufficiency_note(web_results)

        # ── Format sourcing evidence snippets ────────────────────────────────
        if sr.evidence:
            evidence_text = "\n".join(f"- {e}" for e in sr.evidence)
        else:
            evidence_text = "No direct evidence snippets available from sourcing."

        # Format dimension scores summary for richer context
        dim_lines = []
        for dim, ds in sr.dimension_scores.items():
            dim_lines.append(
                f"  {dim}: {ds.score}/5.0 — {ds.rationale}"
            )
        score_context = (
            f"Total score: {sr.total_score}/25.0\n"
            + "\n".join(dim_lines)
            + f"\nSummary: {sr.score_rationale}"
        )

        # ── Step 1b: Industry research evidence — highest priority ─────────────
        industry_evidence_text = self._fetch_industry_evidence(startup.name)

        # ── Step 1c: Paper evidence — sector technology + company comparison ──
        paper_evidence_text = self._fetch_paper_evidence(startup.name)

        # ── Step 1c: ClinicalTrials.gov — pipeline / phase verification ────────
        clinical_trials_text = self._fetch_clinical_trials(startup.name)

        # ── Step 1d: PubMed — academic background for technology / moat ─────────
        pubmed_evidence_text = self._fetch_pubmed_evidence(startup.name)

        prompt = self._render_prompt(
            company_name=startup.name,
            company_profile_json=startup.model_dump_json(indent=2),
            score_rationale=score_context,
            evidence_snippets=evidence_text,
            web_evidence=web_evidence_text,
            evidence_sufficiency_note=evidence_sufficiency_note,
            industry_report_evidence=industry_evidence_text,
            paper_evidence=paper_evidence_text,
            clinical_trials_data=clinical_trials_text,
            pubmed_evidence=pubmed_evidence_text,
        )

        raw = self._call_llm(
            user_prompt=prompt,
            system_prompt=(
                "You are a senior investment analyst. "
                "Return your analysis ONLY as a valid JSON object — no prose, no markdown fences."
            ),
        )

        try:
            data = self._parse_json(raw)
            # Strip placeholder URLs from evidence before constructing the memo
            data = self._filter_evidence(data, startup.name)
            # Inject the startup profile — the LLM does not return it
            data["startup"] = startup.model_dump()
            memo = CompanyDiligenceMemo(**data)
            logger.info(
                "[DiligenceAgent] Memo complete: %s | conviction=%s | "
                "evidence=%d | inferences=%d | risks=%d",
                startup.name,
                memo.overall_conviction,
                len(memo.evidence),
                len(memo.inferences),
                len(memo.key_risks),
            )
            return memo
        except Exception as exc:
            logger.error(
                "[DiligenceAgent] Failed to parse memo for %s: %s",
                startup.name,
                exc,
            )
            return None

    def _fetch_industry_evidence(self, company_name: str) -> str:
        """
        从行业研报中检索该公司所在赛道的技术路线、商业模式和竞争格局背景。

        用途限制（在 prompt 中强制执行）：
          - 仅用于：技术路线对比、商业模式描述、行业竞争格局
          - 不可用于：公司特定事实（融资额、合作金额、临床阶段）

        运行 2 类查询，去重后限制在 3 chunks 以控制 context 用量。
        """
        if self.industry_retriever is None or self.industry_retriever.is_empty:
            return (
                "## 行业研报背景（技术/商业模式参考）\n\n"
                "data/industryresearch/ 目录下暂无研报，"
                "技术路线和商业模式描述需使用弱化语气。"
            )

        seen: set = set()
        merged: list = []

        # Query 1: 该公司所在技术方向的行业背景
        q1 = f"AI制药 {company_name} 技术路线 商业模式"
        for r in self.industry_retriever.search_industry_reports(q1, top_k=2):
            key = (r.source_file, r.chunk_index)
            if key not in seen:
                seen.add(key)
                merged.append(r)

        # Query 2: 行业竞争格局通用背景
        q2 = "AI制药 竞争格局 降本增效 数据壁垒"
        for r in self.industry_retriever.search_industry_reports(q2, top_k=2):
            key = (r.source_file, r.chunk_index)
            if key not in seen:
                seen.add(key)
                merged.append(r)

        merged = merged[:3]
        logger.info(
            "[DiligenceAgent] Industry report evidence for '%s': %d chunks.",
            company_name, len(merged),
        )
        return self.industry_retriever.format_for_llm(
            merged,
            label=f"行业研报背景（技术/商业模式参考 — {company_name}）",
            max_chars_per_chunk=600,
        )

    def _fetch_paper_evidence(self, company_name: str) -> str:
        """
        Query the paper retriever for industry-level context relevant to
        this company's technology and sector.

        Two queries are run and deduplicated by source_file:
          1. Company name + technology
          2. Sector-level AI drug discovery methodology

        Returns a formatted text block ready for prompt injection.
        """
        if self.paper_retriever is None or self.paper_retriever.is_empty:
            return (
                "## Academic & Industry Paper Evidence\n\n"
                "No paper evidence available. "
                "Do NOT make strong technology or competitive claims without an independent source."
            )

        seen_files: set = set()
        merged: list = []

        # Query 1: company-specific technology context
        q1 = f"{company_name} AI drug discovery technology platform"
        for r in self.paper_retriever.search_papers(q1, top_k=3):
            key = (r.source_file, r.chunk_index)
            if key not in seen_files:
                seen_files.add(key)
                merged.append(r)

        # Query 2: sector methodology (moat / competitive landscape context)
        q2 = f"AI generative chemistry protein design clinical pipeline machine learning"
        for r in self.paper_retriever.search_papers(q2, top_k=3):
            key = (r.source_file, r.chunk_index)
            if key not in seen_files:
                seen_files.add(key)
                merged.append(r)

        # Cap at 5 chunks total to stay within context budget
        merged = merged[:5]
        return self.paper_retriever.format_for_llm(
            merged,
            label=f"Academic & Industry Paper Evidence (context for {company_name})",
        )

    def _fetch_clinical_trials(self, company_name: str) -> str:
        """
        Fetch verified clinical trial data for a private company.

        Strategy:
          1. Look up known drugs from COMPANY_DRUG_MAP for targeted queries.
          2. Fall back to a company-name search if no known drugs.
          3. Deduplicate by NCT ID.

        Returns formatted text block ready for prompt injection.
        If no provider is configured, returns a "not available" notice.
        """
        provider = self.clinical_trials_provider
        if provider is None:
            return (
                "## ClinicalTrials.gov Data\n\n"
                "ClinicalTrialsProvider not configured. "
                "Do NOT infer phase, timing, or enrollment status."
            )

        seen_ncts: set = set()
        studies: list = []

        # Query known drugs first (most precise)
        known_drugs = COMPANY_DRUG_MAP.get(company_name, [])
        for drug in known_drugs:
            for s in provider.get_drug_trials(drug, max_results=3):
                if s.nct_id not in seen_ncts:
                    seen_ncts.add(s.nct_id)
                    studies.append(s)

        # If no hits via drug map, try company-name search
        if not studies:
            for s in provider.search_studies(company_name, max_results=3):
                if s.nct_id not in seen_ncts:
                    seen_ncts.add(s.nct_id)
                    studies.append(s)

        logger.info(
            "[DiligenceAgent] ClinicalTrials for '%s': %d verified trial(s).",
            company_name, len(studies),
        )
        return provider.format_for_llm(
            studies,
            label=f"ClinicalTrials.gov — {company_name} Pipeline",
        )

    def _fetch_pubmed_evidence(self, company_name: str) -> str:
        """
        Query PubMed for academic background relevant to this company's
        technology approach and competitive landscape.

        Two queries are run and deduplicated by PMID:
          1. Company name + technology (may return results for known companies)
          2. Sector-level technology methodology

        Returns a formatted text block ready for prompt injection.
        Capped at 4 articles to stay within context budget.

        Usage constraint (enforced in prompt):
          PubMed abstracts are academic background only.
          They must NOT be used to support company-specific facts.
        """
        if self.pubmed_provider is None:
            return (
                "## PubMed Evidence\n\n"
                "PubMedProvider not configured. "
                "Use hedged language for technology and competitive claims "
                "not supported by local paper evidence or web sources."
            )

        seen_pmids: set = set()
        merged: list = []

        # Query 1: company-specific technology
        q1 = f"{company_name} AI drug discovery technology"
        for a in self.pubmed_provider.search_pubmed(q1, max_results=2):
            if a.pmid not in seen_pmids:
                seen_pmids.add(a.pmid)
                merged.append(a)

        # Query 2: sector-level technology methodology
        q2 = "generative chemistry protein design AI drug discovery machine learning"
        for a in self.pubmed_provider.search_pubmed(q2, max_results=4):
            if a.pmid not in seen_pmids:
                seen_pmids.add(a.pmid)
                merged.append(a)

        # Cap at 4 articles total
        merged = merged[:4]
        logger.info(
            "[DiligenceAgent] PubMed evidence for '%s': %d article(s).",
            company_name,
            len(merged),
        )
        return self.pubmed_provider.format_for_llm(
            merged,
            label=f"PubMed Evidence (academic background for {company_name})",
            max_chars_per_abstract=450,
        )

    @staticmethod
    def _build_evidence_sufficiency_note(
        web_results: List[PrivateCompanySearchResult],
    ) -> str:
        """
        Build a plain-English note for the LLM about the quality and quantity
        of web evidence available for this company.

        Three tiers:
          - No results at all → warn that sourcing data is the only basis
          - Results exist but all low/medium quality → reduce confidence
          - ≥1 high or medium-high quality source → normal operation
        """
        if not web_results:
            return (
                "⚠️  No real-time web evidence was retrieved for this company. "
                "Base your analysis ONLY on the sourcing evidence snippets below. "
                "All specific claims must use hedged language: "
                "\"based on limited public information\" or \"per sourcing data only\". "
                "Do NOT state specific numbers without a verifiable source."
            )

        high_quality = [r for r in web_results if r.reliability in ("high", "medium-high")]
        if not high_quality:
            return (
                "⚠️  Web search returned results but none from high-quality sources "
                "(all are media/unknown reliability). "
                "Claims based solely on media coverage must include the caveat "
                "\"per media reports, not independently verified\". "
                "Do NOT use media-only sources to justify specific numbers or conviction upgrades."
            )

        return (
            f"✓  {len(high_quality)} high/medium-high quality source(s) available "
            f"out of {len(web_results)} total web results. "
            "Anchor specific claims to the URLs listed in the web evidence section above. "
            "Claims supported only by media sources (reliability: medium) must be "
            "labelled \"per media reports\"."
        )

    @staticmethod
    def _filter_evidence(data: dict, company_name: str) -> dict:
        """
        Remove evidence items whose source is a placeholder URL.

        Items with fake sources (example.com, etc.) are silently discarded
        rather than being passed downstream as cited facts.  A warning is
        logged for each removal so engineers can track LLM compliance.
        """
        raw_evidence = data.get("evidence", []) or []
        clean, removed = [], []
        for item in raw_evidence:
            src = item.get("source", "") if isinstance(item, dict) else ""
            if is_placeholder_url(src):
                removed.append(src)
            else:
                clean.append(item)
        if removed:
            logger.warning(
                "[DiligenceAgent] %s: discarded %d evidence item(s) with "
                "placeholder URL(s): %s",
                company_name,
                len(removed),
                removed,
            )
        data = dict(data)
        data["evidence"] = clean
        return data

    @staticmethod
    def _save_markdown(
        memos: List[CompanyDiligenceMemo], output_dir: Path
    ) -> None:
        """Save all memos as a single Markdown document to outputs/{run_id}/memos.md."""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "memos.md"

        sections = [
            "# Investment Diligence Memos",
            "",
            f"*{len(memos)} companies analysed*",
            "",
            "---",
            "",
        ]
        for memo in memos:
            sections.append(memo.to_markdown())
            sections.append("")
            sections.append("---")
            sections.append("")

        path.write_text("\n".join(sections), encoding="utf-8")
        logger.info(
            "[DiligenceAgent] Saved %d memo(s) → %s", len(memos), path.name
        )
