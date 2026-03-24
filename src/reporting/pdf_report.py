"""
pdf_report.py — generate report_v2.pdf from report_v2.html (or Word fallback).

Strategy:
  1. Try xhtml2pdf (pure-Python, no GTK needed) on report_v2.html → report_v2.pdf
  2. If that fails, fall back to docx2pdf (uses MS Word COM on Windows) on report.docx
"""
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _pdf_via_xhtml2pdf(html_path: Path, pdf_path: Path) -> bool:
    """Convert HTML → PDF using xhtml2pdf. Returns True on success."""
    try:
        from xhtml2pdf import pisa
    except ImportError:
        logger.warning("[PdfReport] xhtml2pdf not installed.")
        return False

    html_text = html_path.read_text(encoding="utf-8")

    # xhtml2pdf can't handle some modern CSS — strip problematic rules so it
    # doesn't crash, while keeping layout readable.
    # Remove @media queries and CSS variables that confuse the parser.
    html_text = re.sub(r"@media[^{]+\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "", html_text)
    html_text = re.sub(r"var\(--[^)]+\)", "#333333", html_text)

    # Rewrite image src so xhtml2pdf can resolve them (absolute file:// paths)
    base_dir = html_path.parent
    def _abs_src(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith("http") or src.startswith("data:"):
            return m.group(0)
        abs_path = (base_dir / src).resolve()
        return f'src="{abs_path.as_posix()}"'
    html_text = re.sub(r'src="([^"]+)"', _abs_src, html_text)

    try:
        with open(str(pdf_path), "wb") as fh:
            result = pisa.CreatePDF(html_text, dest=fh, encoding="utf-8")
        if result.err:
            logger.warning("[PdfReport] xhtml2pdf reported errors: %s", result.err)
            return False
    except Exception as exc:
        logger.warning("[PdfReport] xhtml2pdf threw an exception: %s", exc)
        if pdf_path.exists():
            pdf_path.unlink()
        return False

    logger.info("[PdfReport] xhtml2pdf → %s", pdf_path)
    return True


def _pdf_via_docx2pdf(docx_path: Path, pdf_path: Path) -> bool:
    """Convert docx → PDF using docx2pdf (requires MS Word on Windows). Returns True on success."""
    try:
        from docx2pdf import convert
    except ImportError:
        logger.warning("[PdfReport] docx2pdf not installed.")
        return False

    try:
        convert(str(docx_path), str(pdf_path))
        logger.info("[PdfReport] docx2pdf → %s", pdf_path)
        return True
    except Exception as exc:
        logger.warning("[PdfReport] docx2pdf failed: %s", exc)
        return False


def generate_pdf_report(
    output_dir: Path,
    html_path: Optional[Path] = None,
    docx_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Generate report_v2.pdf in output_dir.
    Tries xhtml2pdf on report_v2.html first; falls back to docx2pdf on report.docx.
    Returns the PDF path on success, None on failure.
    """
    pdf_path = output_dir / "report_v2.pdf"

    html_path = html_path or (output_dir / "report_v2.html")
    docx_path = docx_path or (output_dir / "report.docx")

    # Strategy 1: xhtml2pdf from HTML
    if html_path.exists():
        if _pdf_via_xhtml2pdf(html_path, pdf_path):
            return pdf_path
        logger.warning("[PdfReport] xhtml2pdf failed; trying docx2pdf fallback.")

    # Strategy 2: docx2pdf
    if docx_path.exists():
        if _pdf_via_docx2pdf(docx_path, pdf_path):
            return pdf_path
        logger.warning("[PdfReport] docx2pdf also failed.")

    logger.error("[PdfReport] Could not generate PDF — all methods failed.")
    return None
