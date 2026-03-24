"""
ReportWriterAgent: synthesizes all validated research into a final investment report.

Input:
  - List[CompanyDiligenceMemo]  (from DiligenceAgent)
  - List[PublicCompanyProfile]  (from PublicMarketAgent)
  - List[CatalystEvent]         (from PublicMarketAgent)
  - ValidationReport            (from ValidatorAgent)
  - output_dir: Path            (run-specific output directory from orchestrator)

Output: FinalReport  →  saved as outputs/{run_id}/final_report.md
"""
import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from src.models.company import PublicCompanyProfile, CatalystEvent
from src.models.report import CompanyDiligenceMemo, ValidationReport, FinalReport
from src.retrieval.paper_retriever import PaperRetriever
from src.retrieval.industry_research_retriever import IndustryResearchRetriever
from src.providers.pubmed_provider import PubMedProvider
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


def _number_citations(text: str) -> str:
    """Replace [来源：xxx] inline citations with numbered refs [N] and append a source list."""
    sources: list = []
    source_map: dict = {}

    def replace(m: re.Match) -> str:
        citation = m.group(1).strip()
        if citation not in source_map:
            source_map[citation] = len(sources) + 1
            sources.append(citation)
        return f"[{source_map[citation]}]"

    processed = re.sub(r'\[来源：([^\]]+)\]', replace, text)
    if sources:
        notes = "\n\n---\n\n## 资料来源\n\n"
        for i, src in enumerate(sources, 1):
            notes += f"[{i}] {src}\n"
        processed += notes
    return processed



class ReportWriterAgent(BaseAgent):
    """
    Aggregates all prior agent outputs into a professional 8-section research report.
    Saves the rendered Markdown to the run-specific output directory.
    """

    prompt_file = "report_writer.md"

    def __init__(
        self,
        config,
        paper_retriever: Optional[PaperRetriever] = None,
        pubmed_provider=None,
        industry_retriever: Optional[IndustryResearchRetriever] = None,
    ):
        super().__init__(config)
        self.paper_retriever = paper_retriever
        self.pubmed_provider = pubmed_provider
        self.industry_retriever = industry_retriever

    def run(
        self,
        diligence_memos: List[CompanyDiligenceMemo],
        public_companies: List[PublicCompanyProfile],
        catalysts: List[CatalystEvent],
        validation_report: ValidationReport,
        output_dir: Optional[Path] = None,
        market_data_note: Optional[str] = None,
    ) -> FinalReport:
        from datetime import datetime as _dt
        _meta: dict = {
            "market_data_source": market_data_note,  # None → omit citation in report
        }
        context = json.dumps(
            {
                "_meta": _meta,
                "company_diligence_memos": [m.model_dump() for m in diligence_memos],
                "public_company_profiles": [c.model_dump() for c in public_companies],
                "catalyst_events": [cat.model_dump() for cat in catalysts],
                "validation": validation_report.model_dump(),
            },
            indent=2,
        )
        industry_evidence_text = self._fetch_industry_evidence()
        paper_evidence_text = self._fetch_paper_evidence()
        pubmed_evidence_text = self._fetch_pubmed_evidence()
        prompt = self._render_prompt(
            research_context=context,
            industry_report_evidence=industry_evidence_text,
            paper_evidence=paper_evidence_text,
            pubmed_evidence=pubmed_evidence_text,
        )

        raw = self._call_llm(
            user_prompt=prompt,
            system_prompt=(
                "你是一名资深卖方研究员，正在撰写面向机构投资者的中文行业深度研究报告。"
                "报告必须全程使用中文，风格对齐中国头部券商研报（中邮证券、国金证券、华泰证券）。"
                "【语言风格规则——严格执行】"
                "禁止使用：我们认为、可以看到、值得关注、或许、可能、也许。"
                "禁止使用：主观表达、论文式长句。"
                "必须使用：客观判断句（无主语），短句+bullet points，先结论后展开。"
                "【数据来源规则——严格执行】"
                "若 _meta.market_data_source 非null，在二级市场表格下方注明：数据来源：[该值]。"
                "若为null，不注明数据来源。"
                "禁止出现：JSON、内部数据、mock、研究背景、internal data、structured data。"
                "所有股价/市值/EV/Revenue数字必须来自 public_company_profiles。"
                "【输出格式——严格执行】"
                "直接输出 Markdown 报告正文，从 ## 一、行业概览 开始。"
                "不得输出任何 JSON、代码块、前缀文字或解释。"
            ),
        )

        # LLM outputs Markdown directly — no JSON parsing needed
        now_str = _dt.now().strftime("%Y-%m-%d %H:%M")
        # Prepend the report title/metadata header
        header = (
            f"# {self.config.sector} 行业深度研究报告\n"
            f"*生成时间：{now_str}　｜　AI投研系统*\n\n---\n\n"
        )
        full_markdown = header + _number_citations(raw.strip())

        report = FinalReport(
            sector=self.config.sector,
            generated_at=now_str,
            raw_markdown=full_markdown,
        )
        self._save_report(report, output_dir)
        logger.info("[ReportWriterAgent] Report written successfully.")
        return report

    def _fetch_industry_evidence(self) -> str:
        """
        针对 5 类必查主题检索行业研报，作为报告最高优先级证据来源。

        5 类查询（对应 DEFAULT_QUERIES）：
          1. AI制药 市场规模 增长 驱动因素
          2. AI制药 商业模式 数据壁垒
          3. AI制药 竞争格局 龙头 公司
          4. AI制药 应用阶段 临床前 降本增效
          5. AI制药 风险提示

        去重后限制在 10 chunks，控制 context 用量。
        """
        if self.industry_retriever is None or self.industry_retriever.is_empty:
            return (
                "## 行业研报证据（最高优先级）\n\n"
                "**【无研报支持】** data/industryresearch/ 目录下暂无行业研报。\n"
                "对所有行业判断（市场规模、竞争格局、商业模式、增长驱动、风险），"
                "必须使用弱化语气（如：据公开信息、市场普遍认为），"
                "严禁给出无来源的强结论。"
            )

        # 5 类必查 queries
        queries = IndustryResearchRetriever.DEFAULT_QUERIES

        seen: set = set()
        merged: list = []
        for query in queries:
            for r in self.industry_retriever.search_industry_reports(query, top_k=3):
                key = (r.source_file, r.chunk_index)
                if key not in seen:
                    seen.add(key)
                    merged.append(r)

        merged = merged[:10]   # 5 queries × top-3 去重后不超过 10 chunks
        logger.info(
            "[ReportWriterAgent] 行业研报证据：%d chunks，来源文件：%s",
            len(merged),
            ", ".join({r.source_file for r in merged}) if merged else "无",
        )
        return self.industry_retriever.format_for_llm(
            merged,
            label="行业研报证据（最高优先级）",
            max_chars_per_chunk=750,
        )

    def _fetch_paper_evidence(self) -> str:
        """
        Run three targeted queries covering the three report sections that
        require academic grounding:
          1. Industry Overview / executive_summary → sector landscape
          2. Investment Thesis / diligence_highlights → technology & moat
          3. Risk Factors → clinical attrition, regulatory, technical risks

        Deduplicates by (source_file, chunk_index) and caps at 8 chunks total.
        """
        if self.paper_retriever is None or self.paper_retriever.is_empty:
            return (
                "## Academic & Industry Paper Evidence\n\n"
                "No paper evidence loaded. "
                "Industry overview and risk factor sections must use hedged language "
                "and must NOT make strong unsourced quantitative claims."
            )

        sector = self.config.sector
        queries = [
            f"{sector} industry overview market landscape trends 2024 2025",
            f"AI drug discovery platform technology differentiation machine learning",
            f"clinical trial success rate attrition regulatory risk AI biotech",
        ]

        seen: set = set()
        merged: list = []
        for query in queries:
            for r in self.paper_retriever.search_papers(query, top_k=3):
                key = (r.source_file, r.chunk_index)
                if key not in seen:
                    seen.add(key)
                    merged.append(r)

        merged = merged[:8]   # stay within prompt budget
        logger.info(
            "[ReportWriterAgent] Paper evidence: %d chunks from %d unique file(s).",
            len(merged),
            len({r.source_file for r in merged}),
        )
        return self.paper_retriever.format_for_llm(
            merged,
            label="Academic & Industry Paper Evidence",
            max_chars_per_chunk=700,
        )

    def _fetch_pubmed_evidence(self) -> str:
        """
        Query PubMed for academic background supporting the three report
        sections that require academic grounding:
          1. Industry Overview / executive_summary  → sector landscape
          2. Investment Thesis / diligence_highlights → technology & moat
          3. Risk Factors → clinical attrition, regulatory, technical risks

        Deduplicates by PMID and caps at 6 articles total.

        Usage constraint (enforced in prompt):
          PubMed abstracts are academic background only.
          They must NOT support company-specific facts.
        """
        if self.pubmed_provider is None:
            return (
                "## PubMed Evidence\n\n"
                "PubMedProvider not configured. "
                "Use hedged language for industry-level claims not supported "
                "by local paper evidence."
            )

        sector = self.config.sector
        queries = [
            f"{sector} market overview 2024 2025 industry landscape",
            "AI drug discovery generative chemistry protein design platform",
            "clinical trial attrition failure rate regulatory risk AI biotech",
        ]

        seen_pmids: set = set()
        merged: list = []
        for query in queries:
            for a in self.pubmed_provider.search_pubmed(query, max_results=3):
                if a.pmid not in seen_pmids:
                    seen_pmids.add(a.pmid)
                    merged.append(a)

        merged = merged[:6]   # stay within prompt budget
        logger.info(
            "[ReportWriterAgent] PubMed evidence: %d article(s).", len(merged)
        )
        return self.pubmed_provider.format_for_llm(
            merged,
            label="PubMed Evidence (academic background)",
            max_chars_per_abstract=450,
        )

    def _save_report(self, report: FinalReport, output_dir: Optional[Path]) -> None:
        from src.config import OUTPUTS_DIR
        save_dir = output_dir if output_dir is not None else OUTPUTS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = save_dir / "final_report.md"
        filepath.write_text(report.raw_markdown, encoding="utf-8")
        logger.info("[ReportWriterAgent] Saved report to %s", filepath)
