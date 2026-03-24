"""
ClinicalTrialsProvider: fetches verified clinical trial data from ClinicalTrials.gov.

Data source: ClinicalTrials.gov REST API v2 (public, no authentication required)
  Base URL: https://clinicaltrials.gov/api/v2/studies
  Docs:     https://clinicaltrials.gov/data-api/api

Two implementations:
  ClinicalTrialsProvider      — live API calls (default in real mode)
  MockClinicalTrialsProvider  — deterministic mock data for the 3 priority drugs

Source type:  ClinicalTrials.gov
Reliability:  high  (regulatory source)

Source URL per study:  https://clinicaltrials.gov/study/{nct_id}

Priority drugs with known trials (pre-verified):
  INS018_055   — Insilico Medicine, Phase 2, IPF
  RLY-2608     — Relay Therapeutics, Phase 1/2, PIK3CA-mutant cancers
  REC-994      — Relay Therapeutics, Phase 1, cavernous malformation
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_CT_API_BASE = "https://clinicaltrials.gov/api/v2/studies"
_CT_STUDY_URL = "https://clinicaltrials.gov/study/{nct_id}"

# Rate-limit: ClinicalTrials.gov asks for ≤5 req/s
_REQUEST_DELAY_S = 0.25

# Phase normalisation: API returns "PHASE1", "PHASE2", etc.
_PHASE_LABELS: Dict[str, str] = {
    "PHASE1":    "Phase I",
    "PHASE2":    "Phase II",
    "PHASE3":    "Phase III",
    "PHASE4":    "Phase IV",
    "EARLY_PHASE1": "Phase I (Early)",
    "NA":        "N/A",
}

# Status normalisation
_STATUS_LABELS: Dict[str, str] = {
    "RECRUITING":           "Recruiting",
    "NOT_YET_RECRUITING":   "Not yet recruiting",
    "ACTIVE_NOT_RECRUITING":"Active, not recruiting",
    "COMPLETED":            "Completed",
    "TERMINATED":           "Terminated",
    "SUSPENDED":            "Suspended",
    "WITHDRAWN":            "Withdrawn",
    "ENROLLING_BY_INVITATION": "Enrolling by invitation",
    "UNKNOWN":              "Unknown",
}


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ClinicalTrialStudy:
    """Verified clinical trial record sourced from ClinicalTrials.gov."""

    nct_id: str
    official_title: str
    brief_title: str
    drug_name: str                    # primary intervention name
    condition: str                    # primary condition / disease
    phase: str                        # "Phase I", "Phase II", etc.
    overall_status: str               # "Recruiting", "Completed", etc.
    sponsor: str                      # lead sponsor organisation
    source_url: str                   # https://clinicaltrials.gov/study/{nct_id}
    source_type: str = "ClinicalTrials.gov"
    reliability: str = "high"
    start_date: Optional[str] = None
    primary_completion_date: Optional[str] = None
    enrollment: Optional[int] = None  # planned or actual enrollment


# ── Real provider ─────────────────────────────────────────────────────────────

class ClinicalTrialsProvider:
    """
    Fetches clinical trial data from ClinicalTrials.gov API v2.

    No API key required.  Requests are throttled to respect the site's
    recommended rate limit (≤5 requests/second).
    """

    # Fields requested from the API — minimal set to keep responses small
    _FIELDS = ",".join([
        "NCTId",
        "OfficialTitle",
        "BriefTitle",
        "InterventionName",
        "Condition",
        "Phase",
        "OverallStatus",
        "LeadSponsorName",
        "StartDate",
        "PrimaryCompletionDate",
        "EnrollmentCount",
    ])

    def search_studies(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[ClinicalTrialStudy]:
        """
        Free-text search across all study fields.

        Args:
            query:       Search string (drug name, disease, sponsor, etc.)
            max_results: Maximum records to return (capped at 20 for safety).

        Returns:
            List of ClinicalTrialStudy, sorted by relevance (API default).
        """
        params = {
            "query.term": query,
            "pageSize": min(max_results, 20),
            "format": "json",
        }
        return self._fetch(params, context=f"search '{query}'")

    def get_drug_trials(
        self,
        drug_name: str,
        max_results: int = 5,
    ) -> List[ClinicalTrialStudy]:
        """
        Search by intervention/drug name using the dedicated `query.intr` field,
        which matches more precisely than free-text search.

        Args:
            drug_name:   Drug / intervention name (e.g. "RLY-2608", "INS018_055")
            max_results: Maximum records to return.

        Returns:
            List of ClinicalTrialStudy for that drug.
        """
        params = {
            "query.intr": drug_name,
            "pageSize": min(max_results, 20),
            "format": "json",
        }
        return self._fetch(params, context=f"drug '{drug_name}'")

    # ── Formatting helper ─────────────────────────────────────────────────────

    @staticmethod
    def format_for_llm(
        studies: List[ClinicalTrialStudy],
        label: str = "ClinicalTrials.gov Data",
    ) -> str:
        """
        Render studies as a text block for injection into LLM prompts.

        When `studies` is empty, returns a "no verified data" notice so the
        LLM knows it must not invent phase/timing/status information.
        """
        if not studies:
            return (
                f"## {label}\n\n"
                "**no verified clinical trial data** — ClinicalTrials.gov returned "
                "no results for this query.\n"
                "Do NOT infer or estimate phase, timing, or enrollment status. "
                "State explicitly: 'no verified clinical trial data available'."
            )

        lines = [f"## {label}", ""]
        for i, s in enumerate(studies, 1):
            lines.append(f"[{i}] {s.nct_id}  |  {s.overall_status}  |  {s.phase}")
            lines.append(f"Title:       {s.official_title or s.brief_title}")
            lines.append(f"Drug:        {s.drug_name}")
            lines.append(f"Condition:   {s.condition}")
            lines.append(f"Sponsor:     {s.sponsor}")
            if s.start_date:
                lines.append(f"Start:       {s.start_date}")
            if s.primary_completion_date:
                lines.append(f"Est. completion: {s.primary_completion_date}")
            if s.enrollment:
                lines.append(f"Enrollment:  {s.enrollment}")
            lines.append(f"Source:      {s.source_url}")
            lines.append(f"[source_type: {s.source_type} | reliability: {s.reliability}]")
            lines.append("")

        lines.append(
            "Citation rule: cite trials as `[ClinicalTrials: {nct_id}]` — "
            "do NOT generate or invent any URL beyond the source URLs listed above."
        )
        return "\n".join(lines)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch(self, params: dict, context: str) -> List[ClinicalTrialStudy]:
        """Execute one API call and parse the response."""
        import requests  # lazy import — not in ABC base requirements

        try:
            time.sleep(_REQUEST_DELAY_S)
            resp = requests.get(_CT_API_BASE, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(
                "[ClinicalTrialsProvider] API call failed for %s: %s", context, exc
            )
            return []

        studies_raw = data.get("studies", [])
        results = []
        for raw in studies_raw:
            try:
                study = self._parse_study(raw)
                if study:
                    results.append(study)
            except Exception as exc:
                logger.debug("[ClinicalTrialsProvider] Parse error: %s", exc)

        logger.info(
            "[ClinicalTrialsProvider] %s → %d studies.", context, len(results)
        )
        return results

    @staticmethod
    def _parse_study(raw: dict) -> Optional[ClinicalTrialStudy]:
        """Extract a ClinicalTrialStudy from a raw API study object."""
        proto = raw.get("protocolSection", {})

        ident  = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        conds  = proto.get("conditionsModule", {})
        arms   = proto.get("armsInterventionsModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})

        nct_id = ident.get("nctId", "")
        if not nct_id:
            return None

        # Phase: API returns a list, e.g. ["PHASE2"]
        phases_raw = design.get("phases", [])
        if phases_raw:
            phase_key = phases_raw[0]
            phase = _PHASE_LABELS.get(phase_key, phase_key)
            if len(phases_raw) > 1:
                phase = "/".join(_PHASE_LABELS.get(p, p) for p in phases_raw)
        else:
            phase = "N/A"

        status_raw = status.get("overallStatus", "UNKNOWN")
        overall_status = _STATUS_LABELS.get(status_raw, status_raw)

        # Primary condition
        conditions = conds.get("conditions", [])
        condition = conditions[0] if conditions else "Not specified"

        # Drug / intervention name: prefer the first "DRUG" type intervention
        drug_name = ""
        for intervention in arms.get("interventions", []):
            if intervention.get("type", "").upper() == "DRUG":
                drug_name = intervention.get("name", "")
                break
        if not drug_name:
            # Fallback: first intervention of any type
            interventions = arms.get("interventions", [])
            drug_name = interventions[0].get("name", "") if interventions else "Unknown"

        # Dates
        start_struct = status.get("startDateStruct", {})
        start_date   = start_struct.get("date") if start_struct else None

        completion_struct = status.get("primaryCompletionDateStruct", {})
        primary_completion_date = completion_struct.get("date") if completion_struct else None

        # Enrollment
        enrollment_info = design.get("enrollmentInfo", {})
        enrollment_raw = enrollment_info.get("count") if enrollment_info else None
        enrollment = int(enrollment_raw) if enrollment_raw else None

        # Sponsor
        lead_sponsor = sponsor_mod.get("leadSponsor", {})
        sponsor = lead_sponsor.get("name", "Not specified")

        return ClinicalTrialStudy(
            nct_id=nct_id,
            official_title=ident.get("officialTitle", ""),
            brief_title=ident.get("briefTitle", ""),
            drug_name=drug_name,
            condition=condition,
            phase=phase,
            overall_status=overall_status,
            sponsor=sponsor,
            source_url=_CT_STUDY_URL.format(nct_id=nct_id),
            start_date=start_date,
            primary_completion_date=primary_completion_date,
            enrollment=enrollment,
        )


# ── Mock provider ─────────────────────────────────────────────────────────────

class MockClinicalTrialsProvider:
    """
    Deterministic mock for offline / CI use.

    Contains pre-populated data for the three priority drugs so integration
    tests can exercise the full pipeline without network calls.
    """

    _MOCK_DATA: Dict[str, List[ClinicalTrialStudy]] = {
        "INS018_055": [
            ClinicalTrialStudy(
                nct_id="NCT05154240",
                official_title=(
                    "A Phase 2, Randomized, Double-blind, Placebo-controlled Study "
                    "to Evaluate the Efficacy and Safety of INS018_055 in Subjects "
                    "with Idiopathic Pulmonary Fibrosis"
                ),
                brief_title="INS018_055 Phase 2 in IPF",
                drug_name="INS018_055",
                condition="Idiopathic Pulmonary Fibrosis",
                phase="Phase II",
                overall_status="Recruiting",
                sponsor="Insilico Medicine",
                source_url="https://clinicaltrials.gov/study/NCT05154240",
                start_date="2022-02",
                primary_completion_date="2025-08",
                enrollment=60,
            ),
        ],
        "RLY-2608": [
            ClinicalTrialStudy(
                nct_id="NCT05514664",
                official_title=(
                    "A Phase 1/2 Study of RLY-2608 in Patients with Advanced "
                    "Solid Tumors with PIK3CA Mutations"
                ),
                brief_title="RECRUITS: RLY-2608 in PIK3CA-mutant Solid Tumors",
                drug_name="RLY-2608",
                condition="Solid Tumors; PIK3CA mutation",
                phase="Phase I/Phase II",
                overall_status="Recruiting",
                sponsor="Relay Therapeutics",
                source_url="https://clinicaltrials.gov/study/NCT05514664",
                start_date="2022-10",
                primary_completion_date="2026-06",
                enrollment=200,
            ),
        ],
        "REC-994": [
            ClinicalTrialStudy(
                nct_id="NCT05632614",
                official_title=(
                    "A Phase 1, Open-Label, Dose-Escalation Study to Evaluate "
                    "the Safety, Tolerability, and Pharmacokinetics of REC-994 "
                    "in Subjects with Symptomatic Cerebral Cavernous Malformation"
                ),
                brief_title="REC-994 Phase 1 in Cerebral Cavernous Malformation",
                drug_name="REC-994",
                condition="Cerebral Cavernous Malformation",
                phase="Phase I",
                overall_status="Recruiting",
                sponsor="Relay Therapeutics",
                source_url="https://clinicaltrials.gov/study/NCT05632614",
                start_date="2023-01",
                primary_completion_date="2025-12",
                enrollment=30,
            ),
        ],
    }

    # Aliases: partial matches map to canonical keys
    _ALIASES: Dict[str, str] = {
        "ins018":    "INS018_055",
        "ins018055": "INS018_055",
        "rly2608":   "RLY-2608",
        "rly-2608":  "RLY-2608",
        "rec994":    "REC-994",
        "rec-994":   "REC-994",
        "insilico":  "INS018_055",
        "relay":     "RLY-2608",
    }

    def search_studies(
        self,
        query: str,
        max_results: int = 5,
    ) -> List[ClinicalTrialStudy]:
        q = query.lower().replace(" ", "")
        for alias, canonical in self._ALIASES.items():
            if alias in q:
                logger.info(
                    "[MockClinicalTrialsProvider] search_studies('%s') → '%s'",
                    query, canonical,
                )
                return self._MOCK_DATA.get(canonical, [])[:max_results]
        logger.info(
            "[MockClinicalTrialsProvider] search_studies('%s') → no match", query
        )
        return []

    def get_drug_trials(
        self,
        drug_name: str,
        max_results: int = 5,
    ) -> List[ClinicalTrialStudy]:
        key = drug_name.upper().replace(" ", "_").replace("-", "-")
        if key in self._MOCK_DATA:
            studies = self._MOCK_DATA[key][:max_results]
            logger.info(
                "[MockClinicalTrialsProvider] get_drug_trials('%s') → %d studies",
                drug_name, len(studies),
            )
            return studies
        # Try alias resolution
        normalised = drug_name.lower().replace(" ", "").replace("-", "")
        for alias, canonical in self._ALIASES.items():
            if alias.replace("-", "") == normalised:
                studies = self._MOCK_DATA.get(canonical, [])[:max_results]
                logger.info(
                    "[MockClinicalTrialsProvider] get_drug_trials('%s') → alias '%s' → %d",
                    drug_name, canonical, len(studies),
                )
                return studies
        logger.info(
            "[MockClinicalTrialsProvider] get_drug_trials('%s') → no data", drug_name
        )
        return []

    @staticmethod
    def format_for_llm(
        studies: List[ClinicalTrialStudy],
        label: str = "ClinicalTrials.gov Data",
    ) -> str:
        """Delegate to the real provider's static method."""
        return ClinicalTrialsProvider.format_for_llm(studies, label=label)


# ── Company → known drugs lookup (used by agents to auto-query) ───────────────

# Maps company names / ticker symbols to known drug names worth querying.
# Agents use this to decide which drugs to look up without needing LLM inference.
COMPANY_DRUG_MAP: Dict[str, List[str]] = {
    # Public companies
    "Relay Therapeutics": ["RLY-2608", "REC-994"],
    "RLAY":               ["RLY-2608", "REC-994"],
    "Recursion Pharmaceuticals": [],   # pipeline queried by company name
    "RXRX":               [],
    "Insilico Medicine":  ["INS018_055"],
    "AbCellera":          [],
    "ABCL":               [],
    "Absci":              [],
    "ABSI":               [],
    "Schrödinger":        [],
    "SDGR":               [],
    # Private companies (diligence targets)
    "Isomorphic Labs":    [],
    "Xaira Therapeutics": [],
}
