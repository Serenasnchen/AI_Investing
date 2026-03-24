"""
Pydantic data models for agent analysis outputs and the final report.

Naming convention:
  TeamProfile            — team assessment sub-model for CompanyDiligenceMemo
  TechnologyProfile      — technology pathway sub-model
  MoatProfile            — defensibility / data-flywheel sub-model
  PipelineProfile        — clinical / preclinical pipeline sub-model
  BusinessModelProfile   — revenue and partnership model sub-model
  EvidenceItem           — a single cited fact (with source)
  InferenceItem          — an analyst inference (with basis)
  CompanyDiligenceMemo   — full investment memo for one private company
  ValidationIssue        — a single quality issue flagged by the validator
  ValidationReport       — aggregated quality review with confidence level
  FinalReport            — complete investment research report (all sections)
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from .company import StartupProfile, PublicCompanyProfile, CatalystEvent


# ── Investment Memo sub-models ───────────────────────────────────────────────

class TeamProfile(BaseModel):
    """Structured assessment of the founding and leadership team."""

    founder_backgrounds: str = Field(
        description=(
            "Brief description of founders' professional backgrounds "
            "(e.g. ex-DeepMind ML researchers + AstraZeneca drug hunters)"
        )
    )
    pharma_ai_academia_signal: str = Field(
        description="Signal strength: 'strong' | 'moderate' | 'weak'"
    )
    key_strength: Optional[str] = Field(
        None, description="Single most compelling team asset in 1 sentence"
    )
    key_gap: Optional[str] = Field(
        None, description="Most important team weakness or missing capability in 1 sentence"
    )


class TechnologyProfile(BaseModel):
    """Core technology pathway and differentiation."""

    pathway: str = Field(
        description=(
            "Technical approach: e.g. 'structure-based generative chemistry', "
            "'protein language model', 'phenomics + foundation model', 'multiomics integration'"
        )
    )
    foundation_model_relationship: Optional[str] = Field(
        None,
        description=(
            "Relationship to AlphaFold, GPT-class LLMs, or other foundation models "
            "(if applicable); does the company build on, compete with, or extend them?"
        ),
    )
    differentiation: str = Field(
        description=(
            "How this technical approach is differentiated from competitors "
            "(e.g. wet-lab closed-loop vs. pure in-silico)"
        )
    )


class MoatProfile(BaseModel):
    """Defensibility and data-flywheel assessment."""

    data_flywheel_description: str = Field(
        description=(
            "How wet-lab data feeds back into model improvement: "
            "synthesis → assay → retrain cycle, frequency, and scale"
        )
    )
    proprietary_data_scale: Optional[str] = Field(
        None,
        description=(
            "Estimated scale or uniqueness of proprietary training data "
            "(e.g. '10M+ annotated compound-activity pairs across 50+ targets')"
        ),
    )
    compute_platform_advantage: Optional[str] = Field(
        None,
        description=(
            "Any structural compute or platform advantage: cloud partnership, "
            "proprietary hardware, or hyperscaler relationship"
        ),
    )


class PipelineProfile(BaseModel):
    """Clinical and preclinical pipeline status."""

    is_clinical_stage: bool = Field(
        default=False,
        description="True if any programme has entered Phase I or later",
    )
    clinical_stage_label: Optional[str] = Field(
        None,
        description="Highest clinical stage reached: 'Phase I' | 'Phase II' | 'Phase III'",
    )
    key_assets: List[str] = Field(
        default_factory=list,
        description=(
            "Named programmes with stage and indication, "
            "e.g. 'INS018_055 (Phase II, IPF)' or 'Programme A (IND-enabling, oncology)'"
        ),
    )
    latest_milestone: Optional[str] = Field(
        None,
        description="Most recent clinical or preclinical milestone with date if available",
    )


class BusinessModelProfile(BaseModel):
    """Revenue model and partnership structure."""

    primary_model: str = Field(
        description=(
            "'pipeline_first' — own drugs, milestone-free pipeline; "
            "'partnership_first' — pharma partnerships fund R&D; "
            "'saas' — platform licensing; "
            "'hybrid' — both owned pipeline and pharma partnerships"
        )
    )
    revenue_sources: List[str] = Field(
        default_factory=list,
        description=(
            "Specific revenue lines, e.g. 'pharma partnership milestones', "
            "'SaaS licensing fees', 'royalties on partnered drugs'"
        ),
    )
    partnership_details: Optional[str] = Field(
        None,
        description=(
            "Named partners, deal sizes, and terms where publicly disclosed; "
            "estimated total milestone potential if available"
        ),
    )


class EvidenceItem(BaseModel):
    """A single factual claim backed by a verifiable source."""

    claim: str = Field(description="The specific factual claim (1 sentence)")
    source: str = Field(
        description=(
            "Source identifier: a real URL (company website, press release, "
            "ClinicalTrials.gov, SEC filing) or "
            "'company_profile_json: <field>' for provider-supplied data. "
            "Never use placeholder domains such as example.com."
        )
    )
    source_type: Optional[str] = Field(
        None,
        description=(
            "Source type: company_official | press_release | research | "
            "regulatory | media | unknown"
        ),
    )
    reliability: Optional[str] = Field(
        None,
        description="Source reliability: high | medium-high | medium | low",
    )


class InferenceItem(BaseModel):
    """An analyst inference drawn from evidence — explicitly not a cited fact."""

    claim: str = Field(description="The analyst's reasoned inference (1 sentence)")
    basis: str = Field(
        description="The evidence or logical chain this inference is drawn from (1 sentence)"
    )


# ── Main investment memo ─────────────────────────────────────────────────────

class CompanyDiligenceMemo(BaseModel):
    """
    Output unit of DiligenceAgent.

    Full investment memo for one private company.  Contains both structured
    sub-models (for downstream JSON/validation use) and a to_markdown()
    renderer that produces a professional, section-by-section memo for the
    final report's 'Primary Market Analysis' section.
    """

    startup: StartupProfile = Field(
        description="The StartupProfile this memo covers (from SourcingAgent output)"
    )

    # ── Metadata ─────────────────────────────────────────────────────────────
    classification: Optional[str] = Field(
        None,
        description=(
            "Technology bucket inherited from sourcing: "
            "generative_chemistry | protein_design | phenomics | multiomics | "
            "antibody_design | cro_platform | saas_tools | other"
        ),
    )

    # ── Structured memo sections ──────────────────────────────────────────────
    team: Optional[TeamProfile] = Field(
        None, description="Structured team assessment"
    )
    technology: Optional[TechnologyProfile] = Field(
        None, description="Technology pathway and differentiation"
    )
    moat: Optional[MoatProfile] = Field(
        None, description="Defensibility and data-flywheel profile"
    )
    pipeline: Optional[PipelineProfile] = Field(
        None, description="Clinical and preclinical pipeline status"
    )
    business_model: Optional[BusinessModelProfile] = Field(
        None, description="Revenue model and partnership structure"
    )
    competitive_landscape: Optional[str] = Field(
        None, description="Narrative competitive positioning vs. private and public peers"
    )
    bull_case: Optional[str] = Field(
        None,
        description=(
            "2-3 sentence upside scenario: why this company could become a sector winner "
            "and what would trigger a step-change valuation"
        ),
    )
    bear_case: Optional[str] = Field(
        None,
        description=(
            "2-3 sentence downside scenario: key failure modes and what "
            "would make this investment lose money"
        ),
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="3-5 specific risks: clinical, technical, regulatory, commercial, or financial",
    )
    overall_conviction: str = Field(
        default="medium",
        description="Analyst conviction level: 'high' | 'medium' | 'low'",
    )
    conviction_rationale: Optional[str] = Field(
        None,
        description=(
            "1-2 sentence rationale explaining the conviction level: "
            "what drives it and what would change it"
        ),
    )

    # ── Evidence / Inference tracking ────────────────────────────────────────
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Factual claims that are directly supported by a cited source",
    )
    inferences: List[InferenceItem] = Field(
        default_factory=list,
        description=(
            "Analyst inferences drawn from evidence — explicitly labelled "
            "so the ValidatorAgent can distinguish them from facts"
        ),
    )

    # ── Legacy flat fields (kept for ValidatorAgent / ReportWriterAgent compat) ──
    technology_moat: Optional[str] = Field(
        None,
        description=(
            "[Legacy] Flat technology moat description. "
            "Prefer the structured 'technology' and 'moat' fields for new analysis."
        ),
    )
    team_assessment: Optional[str] = Field(
        None,
        description="[Legacy] Flat team assessment string.",
    )
    ip_and_partnerships: Optional[str] = Field(
        None,
        description="[Legacy] Flat IP and partnerships string.",
    )
    investment_thesis: Optional[str] = Field(
        None,
        description="[Legacy] Flat investment thesis string.",
    )

    def to_markdown(self) -> str:
        """Render this memo as a formatted Markdown investment memo section."""
        s = self.startup
        lines: List[str] = []

        # ── Header ────────────────────────────────────────────────────────
        conviction_upper = self.overall_conviction.upper()
        lines.append(f"## {s.name}")
        lines.append("")

        meta: List[str] = []
        if s.stage:
            meta.append(f"**Stage:** {s.stage}")
        if s.founded_year:
            meta.append(f"**Founded:** {s.founded_year}")
        if s.hq:
            meta.append(f"**HQ:** {s.hq}")
        if s.total_funding_usd_m is not None:
            meta.append(f"**Funding:** ${s.total_funding_usd_m:.0f}M")
        if meta:
            lines.append("  |  ".join(meta))

        class_val = self.classification or s.technology_category or "N/A"
        lines.append(
            f"**Classification:** {class_val}  |  **Conviction:** {conviction_upper}"
        )
        lines.append("")
        lines.append("---")
        lines.append("")

        # ── Team ──────────────────────────────────────────────────────────
        if self.team:
            lines.append("### Team")
            lines.append(
                f"**Founder backgrounds:** {self.team.founder_backgrounds}"
            )
            lines.append(
                f"**AI / Pharma / Academia signal:** {self.team.pharma_ai_academia_signal}"
            )
            if self.team.key_strength:
                lines.append(f"**Key strength:** {self.team.key_strength}")
            if self.team.key_gap:
                lines.append(f"**Key gap:** {self.team.key_gap}")
            lines.append("")
        elif self.team_assessment:
            lines.append("### Team")
            lines.append(self.team_assessment)
            lines.append("")

        # ── Technology ────────────────────────────────────────────────────
        if self.technology:
            lines.append("### Technology")
            lines.append(f"**Pathway:** {self.technology.pathway}")
            if self.technology.foundation_model_relationship:
                lines.append(
                    f"**Foundation model relationship:** {self.technology.foundation_model_relationship}"
                )
            lines.append(f"**Differentiation:** {self.technology.differentiation}")
            lines.append("")
        elif self.technology_moat:
            lines.append("### Technology & Moat")
            lines.append(self.technology_moat)
            lines.append("")

        # ── Moat ──────────────────────────────────────────────────────────
        if self.moat:
            lines.append("### Moat")
            lines.append(
                f"**Data flywheel:** {self.moat.data_flywheel_description}"
            )
            if self.moat.proprietary_data_scale:
                lines.append(
                    f"**Proprietary data scale:** {self.moat.proprietary_data_scale}"
                )
            if self.moat.compute_platform_advantage:
                lines.append(
                    f"**Compute / platform advantage:** {self.moat.compute_platform_advantage}"
                )
            lines.append("")

        # ── Pipeline ──────────────────────────────────────────────────────
        if self.pipeline:
            lines.append("### Pipeline")
            if self.pipeline.is_clinical_stage and self.pipeline.clinical_stage_label:
                lines.append(
                    f"**Highest stage:** {self.pipeline.clinical_stage_label}"
                )
            else:
                lines.append("**Clinical stage:** Preclinical / IND-enabling")
            if self.pipeline.key_assets:
                lines.append("**Key assets:**")
                for asset in self.pipeline.key_assets:
                    lines.append(f"- {asset}")
            if self.pipeline.latest_milestone:
                lines.append(
                    f"**Latest milestone:** {self.pipeline.latest_milestone}"
                )
            lines.append("")

        # ── Business Model ────────────────────────────────────────────────
        if self.business_model:
            lines.append("### Business Model")
            lines.append(f"**Model type:** {self.business_model.primary_model}")
            if self.business_model.revenue_sources:
                lines.append(
                    "**Revenue sources:** "
                    + ", ".join(self.business_model.revenue_sources)
                )
            if self.business_model.partnership_details:
                lines.append(
                    f"**Partnership details:** {self.business_model.partnership_details}"
                )
            lines.append("")
        elif self.ip_and_partnerships:
            lines.append("### IP & Partnerships")
            lines.append(self.ip_and_partnerships)
            lines.append("")

        # ── Competitive Landscape ─────────────────────────────────────────
        if self.competitive_landscape:
            lines.append("### Competitive Landscape")
            lines.append(self.competitive_landscape)
            lines.append("")

        # ── Bull Case ─────────────────────────────────────────────────────
        if self.bull_case:
            lines.append("### Bull Case")
            lines.append(self.bull_case)
            lines.append("")
        elif self.investment_thesis:
            lines.append("### Investment Thesis")
            lines.append(self.investment_thesis)
            lines.append("")

        # ── Bear Case / Risks ─────────────────────────────────────────────
        if self.bear_case or self.key_risks:
            lines.append("### Bear Case / Risks")
            if self.bear_case:
                lines.append(self.bear_case)
                lines.append("")
            if self.key_risks:
                lines.append("**Key risks:**")
                for risk in self.key_risks:
                    lines.append(f"- {risk}")
            lines.append("")

        # ── Overall Conviction ────────────────────────────────────────────
        lines.append(f"### Overall Conviction: {conviction_upper}")
        if self.conviction_rationale:
            lines.append(self.conviction_rationale)
        lines.append("")

        # ── Evidence vs Inference ─────────────────────────────────────────
        if self.evidence or self.inferences:
            lines.append("### Evidence vs Inference")
            if self.evidence:
                lines.append("**Evidence (cited sources):**")
                for e in self.evidence:
                    lines.append(f"- {e.claim}  *(Source: {e.source})*")
            if self.inferences:
                if self.evidence:
                    lines.append("")
                lines.append("**Inferences (analyst judgement):**")
                for i in self.inferences:
                    lines.append(f"- {i.claim}  *(Basis: {i.basis})*")
            lines.append("")

        return "\n".join(lines)


# Backward-compatible alias
DiligenceResult = CompanyDiligenceMemo


# ── Validation models ────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    """A single quality issue identified by the ValidatorAgent."""

    severity: str = Field(description="Issue severity: high | medium | low")
    check_type: Optional[str] = Field(
        None,
        description=(
            "Issue category: invalid_source | missing_evidence | unsupported_claim | "
            "conflict | overconfident_inference"
        ),
    )
    section: str = Field(
        description="Origin: SourcingAgent | DiligenceAgent | PublicMarketAgent"
    )
    description: str = Field(description="Specific description of the issue")
    suggested_correction: Optional[str] = Field(
        None, description="Recommended fix or caveat to add"
    )


class ValidationReport(BaseModel):
    """
    Output of ValidatorAgent.
    Aggregated quality review across all prior agent outputs.
    """

    issues: List[ValidationIssue] = Field(default_factory=list)
    overall_confidence: str = Field(
        description="Overall research quality: high | medium | low"
    )
    summary: Optional[str] = Field(
        None, description="2-3 sentence validation summary for the report writer"
    )
    corrected_claims: List[str] = Field(
        default_factory=list,
        description=(
            "List of specific claims that were flagged and corrected, "
            "as short one-liners for the report writer to incorporate"
        ),
    )


# ── Final report ─────────────────────────────────────────────────────────────

class FinalReport(BaseModel):
    """
    Output of ReportWriterAgent.
    中文券商研报风格，5大章节结构。
    """

    sector: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"),
        description="报告生成时间",
    )

    # ── 5 大章节（Optional — 新流程直接使用 raw_markdown）──────────────────────
    industry_overview: Optional[str] = Field(
        None, description="第一章：行业概览（市场规模/增速/驱动因素/竞争格局）"
    )
    private_sourcing: Optional[str] = Field(
        None, description="第二章第一节：一级市场 Sourcing（筛选逻辑/公司清单/Market Map/建议）"
    )
    private_analysis: Optional[str] = Field(
        None, description="第二章第二节：一级市场 Analyzing（2-3家重点公司深度分析）"
    )
    public_market: Optional[str] = Field(
        None, description="第三章：二级市场（核心标的/商业模式差异/催化剂）"
    )
    investment_thesis: Optional[str] = Field(
        None, description="第四章：核心投资逻辑（3-5条判断式 bullet points）"
    )
    risk_factors: Optional[str] = Field(
        None, description="第五章：风险提示（技术/临床/商业化/政策）"
    )
    validation_notes: Optional[str] = Field(
        None, description="数据质量说明（高严重性问题摘要）"
    )
    raw_markdown: Optional[str] = Field(
        None,
        description="LLM直接输出的 Markdown 报告正文（新流程主字段）",
    )

    def to_markdown(self) -> str:
        """
        渲染为中文券商研报风格 Markdown。

        新流程：LLM 直接输出 raw_markdown，此方法仅作为遗留兼容路径。
        若 raw_markdown 已填充则直接返回，否则从字段拼装。
        """
        if self.raw_markdown:
            return self.raw_markdown

        # Fallback: assemble from section fields (legacy JSON path)
        lines = [
            f"# {self.sector} 行业深度研究报告",
            f"*生成时间：{self.generated_at}　｜　AI投研系统*",
            "",
            "---",
            "",
            "## 一、行业概览",
            self.industry_overview or "",
            "",
            "## 二、一级市场分析",
            "",
            "### 2.1 Sourcing：公司筛选与市场地图",
            self.private_sourcing or "",
            "",
            "### 2.2 Analyzing：重点公司深度分析",
            self.private_analysis or "",
            "",
            "## 三、二级市场分析",
            self.public_market or "",
            "",
            "## 四、核心投资逻辑",
            self.investment_thesis or "",
            "",
            "## 五、风险提示",
            self.risk_factors or "",
        ]
        if self.validation_notes:
            lines += [
                "",
                "---",
                "",
                "## 数据质量说明",
                "*以下问题由验证模块标记，已在报告中加注说明。*",
                "",
                self.validation_notes,
            ]
        return "\n".join(lines)
