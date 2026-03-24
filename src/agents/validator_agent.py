"""
ValidatorAgent: quality-checks all prior agent outputs across 4 dimensions.

Input:
  - List[CompanyDiligenceMemo]  (from DiligenceAgent)
  - List[PublicCompanyProfile]  (from PublicMarketAgent)
  - List[CatalystEvent]         (from PublicMarketAgent)

Output: ValidationReport

The 4 check dimensions:
  1. missing_evidence      — specific claims without any cited source
  2. unsupported_claim     — conclusions that don't follow from the provided data
  3. conflict              — contradictions between sections
  4. overconfident_inference — statements presented as certain that are estimates/opinions
"""
import json
import logging
from typing import List

from src.models.company import PublicCompanyProfile, CatalystEvent
from src.models.report import CompanyDiligenceMemo, ValidationIssue, ValidationReport
from .base_agent import BaseAgent, is_placeholder_url

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Receives all prior agent outputs as a combined JSON context.
    Returns a structured ValidationReport with typed issues and an overall confidence level.
    """

    prompt_file = "validator.md"

    def run(
        self,
        diligence_memos: List[CompanyDiligenceMemo],
        public_companies: List[PublicCompanyProfile],
        catalysts: List[CatalystEvent],
    ) -> ValidationReport:
        # ── Pre-scan: deterministic check for placeholder URLs ────────────
        pre_issues = self._pre_scan_placeholder_urls(diligence_memos, public_companies)
        if pre_issues:
            logger.warning(
                "[ValidatorAgent] Pre-scan found %d placeholder URL issue(s) "
                "before LLM call.",
                len(pre_issues),
            )

        context = json.dumps(
            {
                "company_diligence_memos": [m.model_dump() for m in diligence_memos],
                "public_company_profiles": [c.model_dump() for c in public_companies],
                "catalyst_events": [cat.model_dump() for cat in catalysts],
            },
            indent=2,
        )
        prompt = self._render_prompt(research_context=context)

        raw = self._call_llm(
            user_prompt=prompt,
            system_prompt=(
                "You are a rigorous research quality reviewer. "
                "Return your findings ONLY as a valid JSON object — no prose, no markdown fences."
            ),
        )

        try:
            data = self._parse_json(raw)
            report = ValidationReport(**data)
            # Prepend pre-scanned issues so they appear first regardless of LLM output
            report.issues = pre_issues + report.issues
            logger.info(
                "[ValidatorAgent] Found %d issues (%d pre-scan + %d LLM). Confidence: %s.",
                len(report.issues),
                len(pre_issues),
                len(report.issues) - len(pre_issues),
                report.overall_confidence,
            )
            return report
        except Exception as exc:
            logger.error("[ValidatorAgent] Failed to parse validation report: %s", exc)
            return ValidationReport(
                issues=pre_issues,
                overall_confidence="low",
                summary=(
                    "Validation LLM parsing failed — review raw outputs manually. "
                    f"{len(pre_issues)} placeholder URL issue(s) detected in pre-scan."
                    if pre_issues else
                    "Validation parsing failed — review raw outputs manually."
                ),
            )

    # ------------------------------------------------------------------
    # Pre-scan helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pre_scan_placeholder_urls(
        diligence_memos: List[CompanyDiligenceMemo],
        public_companies: List[PublicCompanyProfile],
    ) -> List[ValidationIssue]:
        """
        Deterministically scan all evidence sources and source_urls for
        placeholder/fake domains.  Returns a list of HIGH-severity issues
        that will be prepended to the LLM's findings.

        This runs unconditionally (including in mock mode) so placeholder
        URLs are always caught regardless of LLM behaviour.
        """
        issues: List[ValidationIssue] = []

        for memo in diligence_memos:
            for ev in memo.evidence:
                if is_placeholder_url(ev.source):
                    issues.append(ValidationIssue(
                        severity="high",
                        check_type="invalid_source",
                        section="DiligenceAgent",
                        description=(
                            f"invalid source: placeholder URL '{ev.source}' used as "
                            f"evidence source in memo for {memo.startup.name}. "
                            f"Claim: \"{ev.claim}\""
                        ),
                        suggested_correction=(
                            "Replace with a verified real source (company website, press release, "
                            "ClinicalTrials.gov, SEC filing, or named investor material). "
                            "If no real source exists, move the claim to inferences and use "
                            "hedged language such as 'based on limited public information'."
                        ),
                    ))
            for url in (memo.startup.source_urls or []):
                if is_placeholder_url(url):
                    issues.append(ValidationIssue(
                        severity="high",
                        check_type="invalid_source",
                        section="SourcingAgent",
                        description=(
                            f"invalid source: placeholder URL '{url}' in source_urls "
                            f"for startup {memo.startup.name}."
                        ),
                        suggested_correction=(
                            "Replace with a real URL from the original search results, "
                            "or remove from source_urls if no real source exists."
                        ),
                    ))

        for company in public_companies:
            for url in (company.source_urls or []):
                if is_placeholder_url(url):
                    issues.append(ValidationIssue(
                        severity="high",
                        check_type="invalid_source",
                        section="PublicMarketAgent",
                        description=(
                            f"invalid source: placeholder URL '{url}' in source_urls "
                            f"for public company {company.ticker}."
                        ),
                        suggested_correction=(
                            "Replace with a real source URL or remove the field."
                        ),
                    ))

        return issues
