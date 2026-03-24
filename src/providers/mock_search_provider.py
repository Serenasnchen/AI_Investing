"""
MockSearchProvider: returns pre-written search results for AI Drug Discovery queries.

Simulates what Perplexity / Brave Search would return for typical sourcing queries.
Results are realistic but fictional — for development and course demos only.
"""
import logging
from typing import List

from .search_provider import SearchProvider, SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-written search result bank — keyed by topic cluster
# ---------------------------------------------------------------------------
_RESULTS_PRIVATE_COMPANIES: List[SearchResult] = [
    SearchResult(
        title="Isomorphic Labs raises $600M in landmark AI drug discovery round",
        snippet="Isomorphic Labs, the Alphabet-backed AI drug design spinout from DeepMind, has raised $600M in its first external funding round. The company uses AlphaFold-derived models to predict protein-ligand binding and accelerate small-molecule drug design. Partnerships with Eli Lilly ($1.7B) and Novartis ($1.2B) have validated the platform.",
        url="https://example.com/isomorphic-labs-600m",
        source="news",
        published_date="2024-09-12",
    ),
    SearchResult(
        title="Xaira Therapeutics launches with $1 billion Series A — largest ever for AI biotech",
        snippet="Xaira Therapeutics emerged from stealth with $1B in Series A funding co-led by ARCH Venture Partners and Foresite Capital. The San Francisco-based company is building fully integrated AI foundation models for both molecule generation and target biology, with a dedicated wet-lab facility to generate proprietary training data.",
        url="https://example.com/xaira-1b-series-a",
        source="news",
        published_date="2024-04-23",
    ),
    SearchResult(
        title="Insilico Medicine: Phase II trial for first AI-designed IPF drug (INS018_055)",
        snippet="Insilico Medicine has advanced INS018_055, the world's first fully AI-generated small molecule, into Phase II clinical trials for idiopathic pulmonary fibrosis. The Hong Kong/NYC-based company used its Chemistry42 and Biology42 platforms to identify a novel target and design the molecule in 18 months.",
        url="https://example.com/insilico-phase2",
        source="news",
        published_date="2024-02-08",
    ),
    SearchResult(
        title="Generate Biomedicines: generative AI for therapeutic proteins — $370M Series C",
        snippet="Generate Biomedicines raised $370M in Series C funding to advance its Chroma generative model for protein design. The Flagship Pioneering company can design antibodies, enzymes, and novel protein therapeutics from scratch using protein language models. Lead programs target oncology and autoimmune disease.",
        url="https://example.com/generate-biomedicines-series-c",
        source="news",
        published_date="2023-11-14",
    ),
    SearchResult(
        title="BioMap: China's 100B-parameter biological foundation model for drug discovery",
        snippet="BioMap has developed xTrimoPGLM, a 100-billion-parameter biological language model trained on protein sequences, genomic data, and clinical information. The Beijing/Palo Alto company raised $200M Series B to expand antibody engineering and target discovery capabilities. Backed by Tencent and Hillhouse Capital.",
        url="https://example.com/biomap-foundation-model",
        source="web",
        published_date="2024-01-30",
    ),
    SearchResult(
        title="Variational AI targets rare CNS diseases with multi-parameter molecular optimisation",
        snippet="Vancouver-based Variational AI has developed the Entorian platform, using variational autoencoders and diffusion models to simultaneously optimise multiple drug properties. The company secured $35M Series A and has pharma partnerships in CNS and rare disease. Backed by Amplitude Ventures.",
        url="https://example.com/variational-ai-series-a",
        source="web",
        published_date="2023-07-18",
    ),
    SearchResult(
        title="Atomwise raises $123M Series B for AI-powered drug repurposing and discovery",
        snippet="Atomwise uses deep learning and its AtomNet neural network for structure-based drug discovery and repurposing. The San Francisco company has screened over 3 million compounds and has partnerships with AbbVie, Pfizer, and the Gates Foundation for infectious and CNS diseases.",
        url="https://example.com/atomwise-series-b",
        source="news",
        published_date="2022-08-25",
    ),
    SearchResult(
        title="Exscientia merges with Recursion Pharmaceuticals in $688M deal",
        snippet="Oxford-based Exscientia, which produced the first AI-designed molecule to enter clinical trials, has completed its merger with Recursion Pharmaceuticals. The combined entity trades as RXRX on NASDAQ and integrates Exscientia's automated synthesis robots and generative chemistry platform with Recursion's phenomics OS.",
        url="https://example.com/exscientia-recursion-merger",
        source="news",
        published_date="2025-01-10",
    ),
    SearchResult(
        title="Relation Therapeutics: single-cell AI platform for complex disease target discovery",
        snippet="UK-based Relation Therapeutics uses transformer models trained on single-cell RNA sequencing data to discover novel targets for complex diseases. Backed by Balderton Capital and GV (Google Ventures), the company raised $43M Series A to expand its computational biology platform.",
        url="https://example.com/relation-therapeutics",
        source="web",
        published_date="2023-09-05",
    ),
    SearchResult(
        title="Recursion Pharmaceuticals (RXRX) — AI drug discovery at industrial scale",
        snippet="Recursion Pharmaceuticals runs the Recursion OS, combining high-content cellular imaging (phenomics) with foundation models trained on petabytes of biological data. The Salt Lake City company trades on NASDAQ and has a $2.8B market cap. Key pipeline: REC-994 (cerebral cavernous malformation, Phase II).",
        url="https://example.com/rxrx-overview",
        source="web",
        published_date="2024-12-01",
    ),
    SearchResult(
        title="2024 AI drug discovery funding report: $4.5B raised, mega-rounds dominate",
        snippet="Global AI drug discovery funding reached $4.5B in 2024, up 30% from 2023 despite broader biotech headwinds. Mega-rounds (>$100M) accounted for 70% of total capital. Key trend: investors prefer integrated platforms with wet-lab validation over pure-software AI companies.",
        url="https://example.com/ai-pharma-funding-2024",
        source="web",
        published_date="2025-01-28",
    ),
    SearchResult(
        title="Peptone raises $20M to apply protein biophysics AI to drug design",
        snippet="London-based Peptone combines protein physics simulations with deep learning to predict protein dynamics and design therapeutics targeting intrinsically disordered proteins — historically undruggable. The company raised $20M Seed from Talis Capital and Oxford Science Enterprises.",
        url="https://example.com/peptone-seed",
        source="web",
        published_date="2023-04-12",
    ),
]

_RESULTS_RECENT_FUNDING: List[SearchResult] = [
    SearchResult(
        title="Top 10 AI drug discovery deals of 2024",
        snippet="The ten largest AI pharma funding rounds of 2024: 1. Xaira $1B, 2. Isomorphic Labs $600M, 3. Generate Biomedicines $370M Series C, 4. BioMap $200M, 5. Insilico Medicine $100M pre-IPO, 6. Atomwise $80M extension, 7. Relation Therapeutics $43M, 8. Variational AI $35M, 9. Peptone $20M, 10. Vividion Therapeutics $15M.",
        url="https://example.com/top10-deals-2024",
        source="web",
        published_date="2025-01-05",
    ),
    SearchResult(
        title="NVIDIA backs AI drug discovery with strategic investments in 2024",
        snippet="NVIDIA made strategic equity investments in Recursion ($50M), BioNeMo platform partners, and several AI-biology startups as part of its life sciences ecosystem strategy. The company's DGX Cloud and BioNeMo framework are becoming standard infrastructure for AI pharma research.",
        url="https://example.com/nvidia-ai-pharma-2024",
        source="news",
        published_date="2024-11-20",
    ),
    SearchResult(
        title="Pharma partnerships with AI companies hit record $15B in milestone commitments (2024)",
        snippet="Total milestone commitments from Big Pharma partnerships with AI drug discovery companies reached $15B in 2024. Top deals: Roche-Recursion ($150M upfront), AstraZeneca-Absci, Sanofi-Insilico, BMS-Generate Biomedicines. Companies are moving from pure platform licensing to co-development with ownership stakes.",
        url="https://example.com/pharma-ai-partnerships-2024",
        source="news",
        published_date="2024-12-15",
    ),
]


def _build_result_bank() -> List[SearchResult]:
    """Combine all result clusters into a single deduplicated bank."""
    return _RESULTS_PRIVATE_COMPANIES + _RESULTS_RECENT_FUNDING


class MockSearchProvider(SearchProvider):
    """
    Mock search provider for development / course demos.

    Returns pre-written results relevant to AI Drug Discovery.
    For other sectors, results are still returned (they won't be sector-matched)
    — the LLM in the agent layer will filter appropriately.
    """

    def __init__(self):
        self._bank = _build_result_bank()

    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        logger.info("[MockSearchProvider] query=%r → returning %d mock results.", query, min(num_results, len(self._bank)))
        return self._bank[:num_results]
