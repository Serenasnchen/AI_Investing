"""
PaperLoader: reads all PDF files from data/raw/papers/ and splits them into
searchable text chunks.

Each chunk preserves:
  text          — the chunk text (150–1500 chars)
  source_file   — PDF filename (not full path — safe for citations)
  document_type — always "paper"
  chunk_index   — sequential index within the document
  page_number   — PDF page number (1-based) where the chunk starts

Chunking strategy
-----------------
1. Extract text page-by-page with pypdf.
2. Split each page on double-newline (paragraph boundaries in PDF text).
3. Merge consecutive short fragments until MIN_CHARS is reached.
4. Truncate any fragment longer than MAX_CHARS.
5. Drop fragments that are clearly noise (all-caps headers, < MIN_CHARS after strip).

Usage
-----
    from src.retrieval.paper_loader import load_papers
    chunks = load_papers()          # loads from default DATA_RAW_DIR/papers/
    chunks = load_papers(my_dir)    # loads from a custom path
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Chunking parameters ───────────────────────────────────────────────────────
MIN_CHARS = 150     # minimum chars to keep a chunk (drops headers/footers)
MAX_CHARS = 1_400   # maximum chars per chunk (prevents context overflow)
OVERLAP   = 80      # chars of overlap between adjacent chunks


@dataclass
class PaperChunk:
    """A single text chunk extracted from an academic paper."""
    text: str
    source_file: str           # filename only — used as citation key
    document_type: str = "paper"
    chunk_index: int = 0
    page_number: Optional[int] = None


def load_papers(papers_dir: Optional[Path] = None) -> List[PaperChunk]:
    """
    Load all PDFs from `papers_dir` (defaults to data/raw/papers/).

    Returns a flat list of PaperChunk objects sorted by (source_file, chunk_index).
    Returns an empty list if the directory is missing or contains no PDFs.
    """
    if papers_dir is None:
        from src.config import DATA_RAW_DIR
        papers_dir = DATA_RAW_DIR / "papers"

    if not papers_dir.exists():
        logger.warning("[PaperLoader] Directory not found: %s", papers_dir)
        return []

    pdf_files = sorted(papers_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("[PaperLoader] No PDF files found in %s", papers_dir)
        return []

    all_chunks: List[PaperChunk] = []
    for pdf_path in pdf_files:
        try:
            chunks = _load_one(pdf_path)
            all_chunks.extend(chunks)
            logger.info(
                "[PaperLoader] %s → %d chunks", pdf_path.name, len(chunks)
            )
        except Exception as exc:
            logger.warning("[PaperLoader] Failed to load %s: %s", pdf_path.name, exc)

    logger.info(
        "[PaperLoader] Loaded %d total chunks from %d PDF(s).",
        len(all_chunks),
        len(pdf_files),
    )
    return all_chunks


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_one(pdf_path: Path) -> List[PaperChunk]:
    """Extract and chunk a single PDF file."""
    import pypdf

    reader = pypdf.PdfReader(str(pdf_path))
    source_file = pdf_path.name

    # Collect (page_number, raw_text) tuples
    pages: List[tuple] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((page_num, text))

    # Split pages into fragments, then merge/trim into final chunks
    raw_fragments: List[tuple] = []   # (page_number, fragment_text)
    for page_num, text in pages:
        frags = _split_page(text)
        for f in frags:
            raw_fragments.append((page_num, f))

    chunks = _merge_fragments(raw_fragments, source_file)
    return chunks


def _split_page(text: str) -> List[str]:
    """
    Split a page's text into candidate fragments.

    Uses double-newline as primary separator, with fallback to
    sentence-boundary splitting for very long paragraphs.
    """
    # Normalise whitespace: collapse runs of spaces but keep newlines
    text = re.sub(r" {2,}", " ", text)

    # Split on blank lines first
    parts = re.split(r"\n{2,}", text)
    fragments: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= MAX_CHARS:
            fragments.append(part)
        else:
            # Break very long paragraphs at sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", part)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 <= MAX_CHARS:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        fragments.append(current)
                    current = sent
            if current:
                fragments.append(current)
    return fragments


def _merge_fragments(
    raw_fragments: List[tuple],
    source_file: str,
) -> List[PaperChunk]:
    """
    Merge short fragments into chunks of at least MIN_CHARS,
    cap at MAX_CHARS, and assign chunk indices.
    """
    chunks: List[PaperChunk] = []
    chunk_index = 0
    buffer_text = ""
    buffer_page = None

    for page_num, frag in raw_fragments:
        # Drop obvious noise: very short, all-caps, or page-number lines
        cleaned = frag.strip()
        if len(cleaned) < 40:
            continue
        if _is_noise(cleaned):
            continue

        if buffer_page is None:
            buffer_page = page_num

        if buffer_text:
            buffer_text += "\n" + cleaned
        else:
            buffer_text = cleaned

        if len(buffer_text) >= MIN_CHARS:
            # Truncate if oversized
            emit_text = buffer_text[:MAX_CHARS]
            chunks.append(PaperChunk(
                text=emit_text,
                source_file=source_file,
                chunk_index=chunk_index,
                page_number=buffer_page,
            ))
            chunk_index += 1
            # Carry overlap into next chunk
            buffer_text = buffer_text[-OVERLAP:] if len(buffer_text) > OVERLAP else ""
            buffer_page = page_num

    # Flush remaining buffer
    if buffer_text and len(buffer_text) >= MIN_CHARS // 2:
        chunks.append(PaperChunk(
            text=buffer_text[:MAX_CHARS],
            source_file=source_file,
            chunk_index=chunk_index,
            page_number=buffer_page,
        ))

    return chunks


_NOISE_PATTERNS = re.compile(
    r"^(\d+|[ivxlcdm]+|page \d+|©.*|all rights reserved.*|doi:.*|https?://\S+)$",
    re.IGNORECASE,
)

# Bibliography / reference list detector:
# Lines that look like "123. Author A, Author B et al. Journal Vol (Year)"
_REF_LINE = re.compile(
    r"^\d{1,3}\.\s+\w[\w\-]+\s+\w",   # "123. Lastname F,"
)


def _is_noise(text: str) -> bool:
    """Return True for lines that are purely metadata / headers / footers."""
    stripped = text.strip()
    if _NOISE_PATTERNS.match(stripped):
        return True
    # Lines with ≤3 words and no sentence punctuation → likely a header
    words = stripped.split()
    if len(words) <= 3 and not any(c in stripped for c in ".,:;"):
        return True
    # Bibliography entry: starts with a number + author names, no verb-like content
    if _REF_LINE.match(stripped) and len(words) < 20:
        return True
    return False
