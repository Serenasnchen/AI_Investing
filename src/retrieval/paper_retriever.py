"""
PaperRetriever: keyword-based search over loaded paper chunks.

MVP implementation uses TF-overlap scoring:
  score(chunk, query) = Σ  count(term in chunk) / len(chunk_tokens)
                        term in query_terms ∩ chunk_terms

Normalisation ensures longer chunks don't unfairly dominate shorter ones.

Public API
----------
    retriever = PaperRetriever()          # auto-loads from data/raw/papers/
    results   = retriever.search_papers("generative chemistry transformer", top_k=5)
    text_block = retriever.format_for_llm(results, label="Industry context")

Each SearchResult carries:
    chunk_text   — the matched chunk text
    source_file  — PDF filename (safe citation key)
    score        — relevance score (higher = more relevant)
    page_number  — page within the PDF
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from .paper_loader import PaperChunk, load_papers

logger = logging.getLogger(__name__)

# Terms to ignore when building the inverted index
_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "this", "that", "these", "those",
    "it", "its", "as", "which", "who", "what", "how", "when", "where",
    "not", "also", "than", "more", "such", "their", "they", "we", "our",
    "can", "into", "through", "between", "after", "before",
}


@dataclass
class PaperSearchResult:
    """A ranked chunk returned by PaperRetriever.search_papers()."""
    chunk_text: str
    source_file: str
    score: float
    chunk_index: int
    page_number: Optional[int] = None


class PaperRetriever:
    """
    Loads paper chunks at construction time and builds an in-memory inverted
    index for fast keyword search.

    Args:
        papers_dir: Override the default data/raw/papers/ directory.
    """

    def __init__(self, papers_dir: Optional[Path] = None):
        self._chunks: List[PaperChunk] = load_papers(papers_dir)
        self._index: Dict[str, List[int]] = {}   # token → [chunk indices]
        self._token_sets: List[Set[str]] = []     # pre-tokenised chunks
        self._build_index()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return len(self._chunks) == 0

    def search_papers(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[PaperSearchResult]:
        """
        Return the top_k most relevant chunks for the given query.

        Args:
            query:  Natural-language query string.
            top_k:  Maximum results to return.

        Returns:
            List of PaperSearchResult sorted by descending relevance score.
            Empty list if no chunks are loaded or no matches found.
        """
        if self.is_empty:
            return []

        query_terms = _tokenise(query)
        if not query_terms:
            return []

        # Candidate chunk indices: union of posting lists for all query terms
        candidate_indices: Set[int] = set()
        for term in query_terms:
            candidate_indices.update(self._index.get(term, []))

        if not candidate_indices:
            # Try 3-char prefix fallback (handles partial word matches)
            prefixes = {t[:4] for t in query_terms if len(t) >= 4}
            for term, posting in self._index.items():
                if any(term.startswith(p) for p in prefixes):
                    candidate_indices.update(posting)

        if not candidate_indices:
            return []

        # Score each candidate
        scored = []
        for idx in candidate_indices:
            score = self._score(idx, query_terms)
            if score > 0:
                scored.append((score, idx))

        scored.sort(key=lambda x: -x[0])
        top = scored[:top_k]

        results = []
        for score, idx in top:
            chunk = self._chunks[idx]
            results.append(PaperSearchResult(
                chunk_text=chunk.text,
                source_file=chunk.source_file,
                score=round(score, 4),
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
            ))
        return results

    def format_for_llm(
        self,
        results: List[PaperSearchResult],
        label: str = "Academic & Industry Paper Evidence",
        max_chars_per_chunk: int = 800,
    ) -> str:
        """
        Render search results as a text block ready for LLM prompt injection.

        Format per result:
            [paper: filename.pdf | p.N]
            <chunk text>
        """
        if not results:
            return (
                f"## {label}\n\n"
                "No relevant academic paper evidence found for this query.\n"
                "Do NOT make strong industry-level claims without an independent source."
            )

        lines = [f"## {label}", ""]
        for i, r in enumerate(results, 1):
            page_str = f" | p.{r.page_number}" if r.page_number else ""
            lines.append(f"[{i}] [paper: {r.source_file}{page_str}]")
            # Trim chunk if needed to stay within per-chunk budget
            text = r.chunk_text
            if len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk] + "…"
            lines.append(text)
            lines.append("")
        lines.append(
            "Citation rule: when referencing the above, write "
            "`[paper: <filename>]` — never generate a URL for a paper citation."
        )
        return "\n".join(lines)

    def search_and_format(
        self,
        query: str,
        top_k: int = 5,
        label: Optional[str] = None,
    ) -> str:
        """Convenience: search then immediately format for LLM injection."""
        results = self.search_papers(query, top_k=top_k)
        return self.format_for_llm(results, label=label or f'Papers: "{query}"')

    # ── Index construction ────────────────────────────────────────────────────

    def _build_index(self) -> None:
        """Build inverted index and pre-tokenised chunk sets."""
        if not self._chunks:
            logger.info("[PaperRetriever] No chunks to index.")
            return

        for idx, chunk in enumerate(self._chunks):
            tokens = _tokenise(chunk.text)
            self._token_sets.append(set(tokens))
            for token in tokens:
                self._index.setdefault(token, []).append(idx)

        logger.info(
            "[PaperRetriever] Index built: %d chunks, %d unique tokens.",
            len(self._chunks),
            len(self._index),
        )

    def _score(self, chunk_idx: int, query_terms: Set[str]) -> float:
        """
        TF-overlap score normalised by chunk token count.
        score = matched_terms / max(query_len, 1)
        Bonus multiplier if ≥50% of query terms match.
        """
        chunk_tokens = self._token_sets[chunk_idx]
        matched = query_terms & chunk_tokens
        if not matched:
            return 0.0
        base = len(matched) / max(len(query_terms), 1)
        # Bonus for high coverage
        coverage = len(matched) / max(len(query_terms), 1)
        return base * (1.5 if coverage >= 0.5 else 1.0)


# ── Tokeniser ─────────────────────────────────────────────────────────────────

def _tokenise(text: str) -> Set[str]:
    """
    Lower-case, strip punctuation, remove stop words.
    Returns a set of meaningful tokens.
    """
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS}
