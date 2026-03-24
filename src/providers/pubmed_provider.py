"""
PubMedProvider: searches PubMed via NCBI E-utilities for academic literature.

Data source: NCBI E-utilities (public, no authentication required)
  Base URL:  https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
  Docs:      https://www.ncbi.nlm.nih.gov/books/NBK25501/

Two implementations:
  PubMedProvider      — live API calls (default in real mode)
  MockPubMedProvider  — deterministic mock data for offline / CI use

Rate limits:
  Without API key: ≤3 requests/second (NCBI policy)
  With NCBI_API_KEY env var: ≤10 requests/second

Source type:  pubmed
Reliability:  high  (peer-reviewed source)

Source URL per article:  https://pubmed.ncbi.nlm.nih.gov/{pmid}/

Usage constraint:
  PubMed abstracts are academic background evidence only.
  They must NOT be used to support company-specific facts
  (funding, clinical readouts, partnerships).
  Citation format: [PubMed: PMID]
"""
import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_PUBMED_ARTICLE_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

# Rate limit: NCBI asks ≤3 req/s without key, ≤10 req/s with key
_REQUEST_DELAY_S = 0.4  # conservative: ~2.5 req/s

# Maximum PMIDs per efetch call (NCBI recommends ≤200)
_MAX_PMIDS_PER_FETCH = 20

# Maximum abstract length to return (full text preserved in dataclass;
# format_for_llm truncates separately per context budget)
_MAX_ABSTRACT_CHARS = 3000


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class PubMedArticle:
    """Verified academic article record sourced from PubMed."""

    pmid: str
    title: str
    abstract: str
    journal: str
    publication_date: str             # "YYYY-MM" or "YYYY"
    source_url: str                   # https://pubmed.ncbi.nlm.nih.gov/{pmid}/
    authors: List[str] = field(default_factory=list)
    source_type: str = "pubmed"
    reliability: str = "high"


# ── Real provider ─────────────────────────────────────────────────────────────

class PubMedProvider:
    """
    Searches PubMed and fetches article details via NCBI E-utilities.

    Optional: set NCBI_API_KEY in the environment to increase the rate
    limit from 3 to 10 requests/second.
    """

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("NCBI_API_KEY")

    # ── Public interface ──────────────────────────────────────────────────────

    def search_pubmed(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[PubMedArticle]:
        """
        Search PubMed for articles matching `query`.

        Runs esearch to get PMIDs, then efetch to get full records.

        Args:
            query:       Free-text query string (same syntax as PubMed search).
            max_results: Maximum articles to return (capped at 20 for safety).

        Returns:
            List of PubMedArticle, sorted by relevance (PubMed default).
        """
        pmids = self._esearch(query, max_results=min(max_results, 20))
        if not pmids:
            return []
        return self._efetch(pmids)

    def fetch_pubmed_details(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch full records for a list of PubMed IDs.

        Args:
            pmids: List of PMID strings (e.g. ["12345678", "87654321"]).

        Returns:
            List of PubMedArticle for the supplied PMIDs.
        """
        if not pmids:
            return []
        # Cap batch size to NCBI recommendation
        pmids = pmids[:_MAX_PMIDS_PER_FETCH]
        return self._efetch(pmids)

    # ── Formatting helper ─────────────────────────────────────────────────────

    @staticmethod
    def format_for_llm(
        articles: List[PubMedArticle],
        label: str = "PubMed Evidence",
        max_chars_per_abstract: int = 500,
    ) -> str:
        """
        Render articles as a text block for injection into LLM prompts.

        When `articles` is empty, returns a "no PubMed data" notice so
        the LLM knows it must not make strong unsourced claims.
        """
        if not articles:
            return (
                f"## {label}\n\n"
                "**No PubMed articles retrieved** for this query.\n"
                "Do NOT make strong unsourced industry-level claims. "
                "Use hedged language: 'based on general industry knowledge'."
            )

        lines = [f"## {label}", ""]
        for i, a in enumerate(articles, 1):
            authors_short = (
                ", ".join(a.authors[:3]) + (" et al." if len(a.authors) > 3 else "")
                if a.authors else "Unknown"
            )
            abstract_snippet = (
                a.abstract[:max_chars_per_abstract] + "…"
                if len(a.abstract) > max_chars_per_abstract
                else a.abstract
            ) if a.abstract else "Abstract not available."

            lines.append(f"[{i}] PMID: {a.pmid}  |  {a.publication_date}")
            lines.append(f"Title:    {a.title}")
            lines.append(f"Journal:  {a.journal}")
            lines.append(f"Authors:  {authors_short}")
            lines.append(f"Abstract: {abstract_snippet}")
            lines.append(f"Source:   {a.source_url}")
            lines.append(f"[source_type: {a.source_type} | reliability: {a.reliability}]")
            lines.append("")

        lines.append(
            "Citation rule: cite PubMed articles as `[PubMed: PMID]` — "
            "do NOT generate or invent any URL beyond the source URLs listed above. "
            "PubMed abstracts are academic background only — do NOT use them to "
            "support company-specific facts (funding, partnerships, clinical readouts)."
        )
        return "\n".join(lines)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _base_params(self) -> dict:
        """Common params appended to every request."""
        params: dict = {"db": "pubmed", "retmode": "json"}
        if self._api_key:
            params["api_key"] = self._api_key
        return params

    def _esearch(self, query: str, max_results: int) -> List[str]:
        """Run esearch.fcgi and return a list of PMIDs."""
        import requests

        params = self._base_params()
        params.update({
            "term": query,
            "retmax": max_results,
            "usehistory": "n",
        })
        # esearch uses JSON natively
        params["retmode"] = "json"

        try:
            time.sleep(_REQUEST_DELAY_S)
            resp = requests.get(_ESEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning(
                "[PubMedProvider] esearch failed for '%s': %s", query, exc
            )
            return []

        pmids = data.get("esearchresult", {}).get("idlist", [])
        logger.info(
            "[PubMedProvider] esearch '%s' → %d PMIDs.", query, len(pmids)
        )
        return pmids

    def _efetch(self, pmids: List[str]) -> List[PubMedArticle]:
        """Run efetch.fcgi for a batch of PMIDs and parse XML response."""
        import requests

        params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        if self._api_key:
            params["api_key"] = self._api_key

        try:
            time.sleep(_REQUEST_DELAY_S)
            resp = requests.get(_EFETCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        except Exception as exc:
            logger.warning(
                "[PubMedProvider] efetch failed for PMIDs %s: %s",
                pmids[:3],
                exc,
            )
            return []

        articles = []
        for article_el in root.findall(".//PubmedArticle"):
            try:
                article = self._parse_article(article_el)
                if article:
                    articles.append(article)
            except Exception as exc:
                logger.debug("[PubMedProvider] Parse error: %s", exc)

        logger.info(
            "[PubMedProvider] efetch %d PMID(s) → %d articles parsed.",
            len(pmids),
            len(articles),
        )
        return articles

    @staticmethod
    def _parse_article(el: ET.Element) -> Optional[PubMedArticle]:
        """Extract a PubMedArticle from a <PubmedArticle> XML element."""
        medline = el.find("MedlineCitation")
        if medline is None:
            return None

        pmid_el = medline.find("PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""
        if not pmid:
            return None

        article_el = medline.find("Article")
        if article_el is None:
            return None

        # Title
        title_el = article_el.find("ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        # Abstract — may have multiple <AbstractText> sections
        abstract_parts = []
        for ab_el in article_el.findall(".//AbstractText"):
            label = ab_el.get("Label")
            text = "".join(ab_el.itertext()).strip()
            if text:
                abstract_parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(abstract_parts)[:_MAX_ABSTRACT_CHARS]

        # Journal
        journal_el = article_el.find(".//Journal/Title")
        journal = journal_el.text.strip() if journal_el is not None and journal_el.text else ""

        # Publication date — prefer MedlineDate, else Year/Month/Day
        pub_date = ""
        date_el = article_el.find(".//Journal/JournalIssue/PubDate")
        if date_el is not None:
            medline_date = date_el.find("MedlineDate")
            if medline_date is not None and medline_date.text:
                pub_date = medline_date.text.strip()[:10]
            else:
                year_el  = date_el.find("Year")
                month_el = date_el.find("Month")
                year  = year_el.text.strip()  if year_el  is not None and year_el.text  else ""
                month = month_el.text.strip() if month_el is not None and month_el.text else ""
                pub_date = f"{year}-{month}" if month else year

        # Authors
        authors: List[str] = []
        for author_el in article_el.findall(".//AuthorList/Author"):
            last  = author_el.findtext("LastName",  "")
            fore  = author_el.findtext("ForeName",  "")
            initials = author_el.findtext("Initials", "")
            name_parts = [last, fore or initials]
            name = " ".join(p for p in name_parts if p).strip()
            if name:
                authors.append(name)

        return PubMedArticle(
            pmid=pmid,
            title=title,
            abstract=abstract,
            journal=journal,
            publication_date=pub_date,
            source_url=_PUBMED_ARTICLE_URL.format(pmid=pmid),
            authors=authors,
        )


# ── Mock provider ─────────────────────────────────────────────────────────────

class MockPubMedProvider:
    """
    Deterministic mock for offline / CI use.

    Contains pre-populated abstracts for three representative queries
    covering the AI drug discovery sector.
    """

    _MOCK_ARTICLES: Dict[str, List[PubMedArticle]] = {
        "ai drug discovery": [
            PubMedArticle(
                pmid="37748386",
                title=(
                    "Artificial intelligence in drug discovery and development: "
                    "a comprehensive review"
                ),
                abstract=(
                    "Artificial intelligence (AI) and machine learning (ML) are "
                    "transforming drug discovery by accelerating target identification, "
                    "hit-to-lead optimisation, and preclinical candidate selection. "
                    "Deep learning models trained on large chemical and biological datasets "
                    "have demonstrated the ability to predict binding affinity, ADMET "
                    "properties, and clinical toxicity with accuracy approaching experimental "
                    "benchmarks. Several AI-designed molecules have entered Phase I/II trials, "
                    "validating the end-to-end AI pipeline concept. Key challenges include "
                    "data quality, model interpretability, and prospective validation outside "
                    "retrospective benchmarks."
                ),
                journal="Nature Reviews Drug Discovery",
                publication_date="2023-10",
                source_url="https://pubmed.ncbi.nlm.nih.gov/37748386/",
                authors=["Schneider G", "Fechner N", "Stork C"],
            ),
            PubMedArticle(
                pmid="36849393",
                title=(
                    "Generative AI for de novo drug design: a systematic review "
                    "of architectures and benchmarks"
                ),
                abstract=(
                    "Generative models — including variational autoencoders, generative "
                    "adversarial networks, diffusion models, and large language models — "
                    "have been applied extensively to de novo molecular design. This review "
                    "surveys 150+ papers published 2019-2023, finding that diffusion-based "
                    "methods currently achieve the highest benchmark scores on QED, SA, and "
                    "protein-ligand docking metrics. A persistent gap between in-silico "
                    "benchmark performance and wet-lab confirmation rates remains the field's "
                    "central challenge; fewer than 15% of AI-designed compounds confirm "
                    "activity in orthogonal assays."
                ),
                journal="Journal of Chemical Information and Modeling",
                publication_date="2023-03",
                source_url="https://pubmed.ncbi.nlm.nih.gov/36849393/",
                authors=["Wang M", "Li Y", "Zhang X", "Chen L"],
            ),
        ],
        "generative chemistry": [
            PubMedArticle(
                pmid="36652531",
                title=(
                    "Generative chemistry: drug discovery with deep generative models"
                ),
                abstract=(
                    "Generative deep learning has produced a paradigm shift in small-molecule "
                    "drug discovery. Graph neural networks, transformer-based language models "
                    "trained on SMILES strings, and 3D equivariant diffusion models can now "
                    "generate novel, synthesisable molecules with desired pharmacophoric "
                    "properties. Lead time from target identification to preclinical candidate "
                    "nomination has been reported at 12-18 months for AI-native programmes, "
                    "versus 3-5 years historically. The Insilico Medicine INS018_055 IPF "
                    "programme, reaching Phase 2 in 2023, is the most advanced public "
                    "demonstration of an end-to-end generative chemistry pipeline."
                ),
                journal="Chemical Science",
                publication_date="2023-01",
                source_url="https://pubmed.ncbi.nlm.nih.gov/36652531/",
                authors=["Grisoni F", "Schneider G"],
            ),
        ],
        "protein design": [
            PubMedArticle(
                pmid="37792837",
                title=(
                    "Computational protein design using deep learning: "
                    "from AlphaFold to de novo binders"
                ),
                abstract=(
                    "AlphaFold2 and its successors have fundamentally changed structural "
                    "biology. Building on predicted structures, deep learning protein design "
                    "tools such as ProteinMPNN, RFdiffusion, and ESMFold now enable rational "
                    "design of de novo protein binders, enzymes, and antibody variants "
                    "with experimental success rates of 20-50% for moderate-complexity targets. "
                    "Clinical translation is nascent; the first de novo designed proteins "
                    "entered Phase I trials in 2023-2024. Key barriers include immunogenicity "
                    "prediction, scalable manufacturing, and regulatory precedent for "
                    "computationally-designed biologics."
                ),
                journal="Nature Structural & Molecular Biology",
                publication_date="2023-09",
                source_url="https://pubmed.ncbi.nlm.nih.gov/37792837/",
                authors=["Dauparas J", "Anishchenko I", "Bennett N", "Baker D"],
            ),
            PubMedArticle(
                pmid="37468656",
                title=(
                    "Structure-based drug discovery with deep learning: "
                    "Relay Therapeutics and conformational dynamics"
                ),
                abstract=(
                    "Structure-based drug discovery enhanced by molecular dynamics simulation "
                    "and machine learning can access cryptic binding pockets invisible to "
                    "static crystal structures. Relay Therapeutics' Dynamo platform integrates "
                    "conformational sampling with generative design to address historically "
                    "undruggable targets. The RLY-2608 Phase 1/2 programme in PIK3CA-mutant "
                    "solid tumours represents the first clinical validation of conformational "
                    "dynamics-guided design. Allosteric inhibitor approaches confer potential "
                    "selectivity advantages over orthosteric competitors."
                ),
                journal="Drug Discovery Today",
                publication_date="2023-07",
                source_url="https://pubmed.ncbi.nlm.nih.gov/37468656/",
                authors=["Vajda S", "Cossio P", "Bhattacharyya M"],
            ),
        ],
    }

    # Query keyword → canonical key (substring match)
    _QUERY_MAP = [
        ("ai drug",           "ai drug discovery"),
        ("drug discovery",    "ai drug discovery"),
        ("artificial intell", "ai drug discovery"),
        ("machine learning",  "ai drug discovery"),
        ("generative chem",   "generative chemistry"),
        ("generative mol",    "generative chemistry"),
        ("de novo",           "generative chemistry"),
        ("protein design",    "protein design"),
        ("protein struct",    "protein design"),
        ("alphafold",         "protein design"),
        ("relay",             "protein design"),
        ("insilico",          "generative chemistry"),
    ]

    def search_pubmed(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[PubMedArticle]:
        q = query.lower()
        for keyword, canonical in self._QUERY_MAP:
            if keyword in q:
                results = self._MOCK_ARTICLES.get(canonical, [])[:max_results]
                logger.info(
                    "[MockPubMedProvider] search_pubmed('%s') → canonical='%s' → %d articles",
                    query, canonical, len(results),
                )
                return results
        logger.info(
            "[MockPubMedProvider] search_pubmed('%s') → no match", query
        )
        return []

    def fetch_pubmed_details(self, pmids: List[str]) -> List[PubMedArticle]:
        all_articles = [
            a for articles in self._MOCK_ARTICLES.values() for a in articles
        ]
        result = [a for a in all_articles if a.pmid in pmids]
        logger.info(
            "[MockPubMedProvider] fetch_pubmed_details(%s) → %d articles",
            pmids, len(result),
        )
        return result

    @staticmethod
    def format_for_llm(
        articles: List[PubMedArticle],
        label: str = "PubMed Evidence",
        max_chars_per_abstract: int = 500,
    ) -> str:
        """Delegate to the real provider's static method."""
        return PubMedProvider.format_for_llm(
            articles, label=label, max_chars_per_abstract=max_chars_per_abstract
        )
