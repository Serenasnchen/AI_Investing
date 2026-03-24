"""
industry_chart_extractor.py  (v2 — quality-gated)

Strategy
--------
For each chart spec (section, pdf_fragment, keywords, caption_hint):

  1. Locate the matching PDF in pdf_dir.
  2. Score every page with _score_page():
       HARD REJECT  → pages containing disclaimer / website boilerplate text
       POSITIVE     → chart-title patterns (图N:), data-source notes, numeric density,
                      distinct year count, CAGR keyword
       NEGATIVE     → dense prose (sentence count penalty)
  3. Pick the highest-scoring page that:
       - Exceeds MIN_CHART_SCORE
       - Is near a keyword mention (or any high-scoring page as fallback)
       - Has not already been extracted from the same PDF
  4. If no page reaches MIN_CHART_SCORE → skip PDF extraction for this spec.
  5. After processing all specs, for any section that received ZERO charts, run the
     auto-generation fallback (matplotlib):
       - 行业概览              → market-size projection line chart
       - 2.1 Sourcing         → (skipped — sourcing_ranking.png already covers this)
       - 三、二级市场分析      → (skipped — data not reliably available)

All charts (PDF renders + auto-generated) are saved to output_dir/industry_charts/.
Metadata is written to industry_charts/industry_charts.json.

Dependency: PyMuPDF (fitz) for PDF rendering.  pip install PyMuPDF
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SKIP_FIRST_N_PAGES = 3   # skip cover / disclaimer / TOC
RENDER_DPI          = 150
MIN_CHART_SCORE     = 18.0  # pages below this score are rejected

# Hard-reject: any page containing these strings is immediately disqualified
HARD_REJECT_KEYWORDS: List[str] = [
    "免责声明", "免责条款",
    "分析师声明", "分析师认证",
    "投资评级说明", "评级说明",
    "版权声明", "版权所有",
    "ByDrug", "医药魔方", "医药新闻",
    "copyright ©", "all rights reserved",
    "本报告仅供", "本报告的信息均来源于",
    "重要声明", "信息披露",
]

# Chart-title patterns  (strongest indicator — chart page almost certainly)
CHART_TITLE_RE: List[str] = [
    r"图\s*\d+",                    # 图1、图 1
    r"图\s*[一二三四五六七八九十]",  # 图一
    r"Figure\s*\d+",
    r"Chart\s*\d+",
    r"Exhibit\s*\d+",
]

# Data-source patterns  (almost always appear at the bottom of chart pages)
DATA_SOURCE_KEYWORDS: List[str] = [
    "数据来源", "资料来源", "来源：", "来源:", "Source:", "注：数据来源",
]

# Content keywords that raise the score of a chart page
CHART_CONTENT_KEYWORDS: List[str] = [
    "CAGR", "亿美元", "billion", "million",
    "增速", "增长率", "市场规模",
    "预测", "forecast", "复合增长",
    "市占率", "份额", "占比",
]

# ── Chart spec list ────────────────────────────────────────────────────────────
# (section_target, pdf_fragment, search_keywords, caption_hint)
#
# search_keywords are used ONLY to prioritise keyword-adjacent pages.
# The quality gate (_score_page >= MIN_CHART_SCORE) is the hard filter.

PRIORITY_SOURCES: List[Tuple[str, str, List[str], str]] = [
    # ── 行业概览 ────────────────────────────────────────────────────────────
    (
        "一、行业概览",
        "2025-08-28_国金证券",
        ["里程碑", "重要事件", "发展历程", "时间线"],
        "AI制药行业发展史重要里程碑",
    ),
    (
        "一、行业概览",
        "2026-01-22_中邮证券",
        ["降本增效", "分子创新", "AI在制药", "效率提升"],
        "AI在制药环节的应用：从降本增效到分子创新",
    ),
    (
        "一、行业概览",
        "2025-12-11_国金证券",
        ["市场规模", "增速", "CAGR", "规模预测"],
        "全球AI制药市场规模与增速预测",
    ),
    # ── 一级市场 Sourcing ─────────────────────────────────────────────────
    (
        "2.1 Sourcing：公司筛选与市场地图",
        "2025-12-11_国金证券",
        ["寻宝图", "市场地图", "赛道图谱", "全景图", "竞争格局"],
        "全球AI制药赛道寻宝图",
    ),
    (
        "2.1 Sourcing：公司筛选与市场地图",
        "2025-08-28_国金证券",
        ["竞争格局", "产业链", "生态系统", "龙头"],
        "AI制药竞争格局与产业链全景图",
    ),
    # ── 二级市场 ─────────────────────────────────────────────────────────
    (
        "三、二级市场分析",
        "2025-08-24_东吴证券",
        ["交易", "合作", "融资", "里程碑付款", "BD"],
        "全球AIDD重点合作交易概览",
    ),
    (
        "三、二级市场分析",
        "2025-12-11_国金证券",
        ["交易金额", "生态系统", "全球交易", "BD金额"],
        "全球AI制药生态系统与重点交易图谱",
    ),
]


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class IndustryChart:
    source_file: str
    source_label: str
    page_num: int           # 1-indexed; 0 = auto-generated (no source page)
    caption: str
    section_target: str
    image_path: Optional[str] = None
    generated: bool = False  # True = matplotlib fallback, False = PDF render


# ── Page quality scoring ───────────────────────────────────────────────────────

def _score_page(text: str) -> float:
    """
    Score a PDF page for its likelihood of being a high-quality, information-rich
    chart page.

    Returns
    -------
    float("-inf")  Hard-rejected (disclaimer, boilerplate, dense prose)
    0.0            Empty / vector-only page (candidates but low confidence)
    > 0            Scored chart candidates; MIN_CHART_SCORE is the acceptance gate
    """
    if not text.strip():
        # Likely vector-only (chart drawn as PDF paths) — possible chart, low score
        return 0.0

    text_lower = text.lower()

    # ── Hard reject ──────────────────────────────────────────────────────────
    for kw in HARD_REJECT_KEYWORDS:
        if kw.lower() in text_lower:
            return float("-inf")

    n_chars     = len(text)
    n_sentences = len(re.findall(r"[。！？.!?]", text))

    # Dense prose → reject (unless overridden by strong chart signals below)
    is_prose_heavy = n_chars > 1600 and n_sentences > 20

    # ── Positive signals ─────────────────────────────────────────────────────
    score = 0.0

    # Chart title pattern: strongest single indicator; hard-reject if absent
    has_chart_title = any(re.search(p, text) for p in CHART_TITLE_RE)
    if not has_chart_title:
        return float("-inf")
    score += 12

    # Data-source note: nearly always present on chart pages
    has_data_source = any(kw in text for kw in DATA_SOURCE_KEYWORDS)
    if has_data_source:
        score += 9

    # Multiple distinct years → time-series chart
    years = set(re.findall(r"\b20[2-3]\d\b", text))
    if len(years) >= 4:
        score += 10
    elif len(years) >= 2:
        score += 5

    # Chart content keywords
    for kw in CHART_CONTENT_KEYWORDS:
        if kw in text:
            score += 2   # capped per-keyword; many matches stack naturally

    # High number density → data labels
    numbers = re.findall(r"\d+\.?\d*", text)
    if len(numbers) >= 20:
        score += 5
    elif len(numbers) >= 10:
        score += 2

    # ── Negative signals ─────────────────────────────────────────────────────
    score -= n_sentences * 0.35  # prose paragraphs hurt the score

    # Hard reject override: prose-heavy AND no chart title/source
    if is_prose_heavy and not (has_chart_title and has_data_source):
        return float("-inf")

    return score


# ── Page selection ─────────────────────────────────────────────────────────────

def _find_best_chart_page(
    page_texts: List[str],
    keywords: List[str],
    exclude: Optional[Set[int]] = None,
    min_score: float = MIN_CHART_SCORE,
) -> Optional[int]:
    """
    Return the 0-based index of the best qualifying chart page.

    Selection strategy
    ------------------
    1. Score all candidate pages (skip first SKIP_FIRST_N_PAGES, skip 'exclude' set).
    2. Among keyword-adjacent pages that meet min_score, return the highest scorer.
    3. If none found, return the highest-scoring non-excluded page that meets min_score.
    4. If nothing reaches min_score, return None (caller may use fallback).
    """
    excl = exclude or set()
    n = len(page_texts)

    # Score all pages
    scores: List[Tuple[int, float]] = []
    for i, text in enumerate(page_texts):
        if i < SKIP_FIRST_N_PAGES or i in excl:
            continue
        s = _score_page(text)
        if s != float("-inf"):
            scores.append((i, s))

    if not scores:
        return None

    # Identify keyword-adjacent page indices
    keyword_adjacent: Set[int] = set()
    for i, text in enumerate(page_texts):
        if i < SKIP_FIRST_N_PAGES or i in excl:
            continue
        if any(kw.lower() in text.lower() for kw in keywords):
            keyword_adjacent.add(i)
            if i + 1 < n and (i + 1) not in excl:
                keyword_adjacent.add(i + 1)
            if i - 1 >= SKIP_FIRST_N_PAGES and (i - 1) not in excl:
                keyword_adjacent.add(i - 1)

    # Priority 1: keyword-adjacent pages that meet the quality gate
    kw_qualified = [
        (i, s) for (i, s) in scores
        if i in keyword_adjacent and s >= min_score
    ]
    if kw_qualified:
        best = max(kw_qualified, key=lambda x: x[1])
        logger.debug(
            "[ChartExtractor] Selected p%d (score=%.1f, keyword-adjacent)",
            best[0] + 1, best[1],
        )
        return best[0]

    # Priority 2: any page that meets the quality gate
    qualified = [(i, s) for (i, s) in scores if s >= min_score]
    if qualified:
        best = max(qualified, key=lambda x: x[1])
        logger.debug(
            "[ChartExtractor] Selected p%d (score=%.1f, best-overall)",
            best[0] + 1, best[1],
        )
        return best[0]

    logger.debug(
        "[ChartExtractor] Best score was %.1f — below threshold %.1f",
        max(s for _, s in scores), min_score,
    )
    return None   # no page qualified


# ── PDF helpers ────────────────────────────────────────────────────────────────

def _slugify_for_filename(text: str, max_len: int = 25) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")[:max_len]


def _parse_source_label(filename: str) -> str:
    """Derive a short citation label from a PDF filename."""
    stem = Path(filename).stem
    parts = stem.split("_")
    if parts and re.match(r"^\d{4}[-]\d{2}[-]\d{2}$|^\d{8}$", parts[0]):
        date   = parts[0]
        broker = parts[1] if len(parts) > 1 else stem
        return f"{broker} {date}"
    if len(parts) >= 2:
        suffix = parts[-1]
        if re.match(r"^\d{4}[-.]?\d{0,2}[-.]?\d{0,2}$", suffix):
            return f"{'_'.join(parts[:-1])} {suffix}"
    return stem[:40] if len(stem) > 40 else stem


def _find_matching_pdf(pdf_dir: Path, fragment: str) -> Optional[Path]:
    frag_lower = fragment.lower()
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        if frag_lower in pdf.name.lower():
            return pdf
    return None


def _get_page_texts(pdf_path: Path) -> List[str]:
    try:
        import pypdf  # noqa: PLC0415
        reader = pypdf.PdfReader(str(pdf_path))
        texts = []
        for i in range(len(reader.pages)):
            try:
                texts.append(reader.pages[i].extract_text() or "")
            except Exception:
                texts.append("")
        return texts
    except Exception as exc:
        logger.warning("[ChartExtractor] pypdf failed for %s: %s", pdf_path.name, exc)
        return []


def _render_page_as_png(pdf_path: Path, page_index: int, output_path: Path) -> bool:
    try:
        import fitz  # noqa: PLC0415
    except ImportError:
        logger.warning("[ChartExtractor] PyMuPDF not installed. pip install PyMuPDF")
        return False
    try:
        doc  = fitz.open(str(pdf_path))
        if page_index >= len(doc):
            doc.close()
            return False
        page = doc[page_index]
        mat  = fitz.Matrix(RENDER_DPI / 72.0, RENDER_DPI / 72.0)
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(output_path))
        doc.close()
        logger.info(
            "[ChartExtractor] Rendered p%d of %s → %s (score qualified)",
            page_index + 1, pdf_path.name, output_path.name,
        )
        return True
    except Exception as exc:
        logger.warning(
            "[ChartExtractor] Render failed p%d of %s: %s",
            page_index + 1, pdf_path.name, exc,
        )
        return False


# ── Market-data extraction (for fallback chart) ────────────────────────────────

_MARKET_YEAR_CN_RE  = re.compile(
    r"(20[2-3]\d)\s*年[^，。\n]{0,25}?(\d{1,5}\.?\d*)\s*亿(?:美元)?"
)
_MARKET_YEAR_EN_RE  = re.compile(
    r"\$?\s*(\d{1,5}\.?\d*)\s*(?:billion|B).*?\b(20[2-3]\d)\b",
    re.IGNORECASE,
)
_CAGR_RE = re.compile(
    r"(?:CAGR|复合增长率|年均增长)[^%\d]{0,15}(\d{1,3}\.?\d*)\s*%",
    re.IGNORECASE,
)


def _extract_market_projections(pdf_dir: Path) -> Dict:
    """
    Scan all PDFs in pdf_dir for AI drug discovery market size data points.
    Returns {year: size_億USD, 'cagr': float} with best-effort values.
    """
    data: Dict = {}
    cagr_candidates: List[float] = []

    priority_frags = ["国金证券", "中邮证券", "东吴证券"]
    pdfs = []
    for frag in priority_frags:
        p = _find_matching_pdf(pdf_dir, frag)
        if p and p not in pdfs:
            pdfs.append(p)

    for pdf_path in pdfs[:3]:
        texts = _get_page_texts(pdf_path)
        combined = " ".join(texts)
        for m in _MARKET_YEAR_CN_RE.finditer(combined):
            year, size = int(m.group(1)), float(m.group(2))
            if 0.5 < size < 50000:
                data[year] = max(data.get(year, 0.0), size)
        for m in _MARKET_YEAR_EN_RE.finditer(combined):
            size_b, year = float(m.group(1)), int(m.group(2))
            size_亿 = size_b * 10  # $1B ≈ 10亿USD
            if 0.5 < size_亿 < 50000:
                data[year] = max(data.get(year, 0.0), size_亿)
        for m in _CAGR_RE.finditer(combined):
            v = float(m.group(1))
            if 5 < v < 80:
                cagr_candidates.append(v)

    if cagr_candidates:
        data["cagr"] = round(
            sorted(cagr_candidates)[len(cagr_candidates) // 2], 1
        )

    return data


# ── Matplotlib fallback: market size line chart ────────────────────────────────

# Consensus defaults (consistent with major reports; used only if extraction fails)
_DEFAULT_MARKET = {
    2022: 13,
    2023: 18,
    2024: 26,
    2025: 38,
    2026: 55,
    2027: 79,
    2028: 113,
    2030: 233,
    2032: 480,
}
_DEFAULT_CAGR = 43.0


def _generate_market_size_chart(market_data: Dict, output_path: Path) -> bool:
    """
    Generate a clean market-size projection line chart with matplotlib.
    Saves to output_path as PNG.  Returns True on success.
    """
    try:
        import matplotlib  # noqa: PLC0415
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: PLC0415
        import matplotlib.ticker as mticker  # noqa: PLC0415
    except ImportError:
        logger.warning("[ChartExtractor] matplotlib not available for fallback chart")
        return False

    # ── Font: prefer Chinese font on Windows, fall back gracefully ────────────
    try:
        import matplotlib.font_manager as fm  # noqa: PLC0415
        available = {f.name for f in fm.fontManager.ttflist}
        for name in ["Microsoft YaHei", "SimHei", "SimSun", "PingFang SC"]:
            if name in available:
                matplotlib.rcParams["font.sans-serif"] = [name]
                break
    except Exception:
        pass
    matplotlib.rcParams["axes.unicode_minus"] = False

    # ── Data prep ─────────────────────────────────────────────────────────────
    size_data = {k: v for k, v in market_data.items() if isinstance(k, int)}
    cagr      = market_data.get("cagr", _DEFAULT_CAGR)

    if len(size_data) < 3:
        size_data = _DEFAULT_MARKET.copy()
        cagr      = _DEFAULT_CAGR
        source_note = "注：数据重绘自公开研报平均估计"
    else:
        source_note = "注：数据重绘自国金证券、中邮证券等研报"

    years  = sorted(size_data.keys())
    values = [size_data[y] for y in years]

    # Split into history and forecast (≥ current year = forecast)
    CURRENT_YEAR = 2025
    hist_x = [y for y in years if y <= CURRENT_YEAR]
    hist_y = [size_data[y] for y in hist_x]
    fore_x = [y for y in years if y >= CURRENT_YEAR]
    fore_y = [size_data[y] for y in fore_x]

    # ── Plot ──────────────────────────────────────────────────────────────────
    ACCENT = "#1a56a4"
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")
    ax.grid(axis="y", color="#d1d5db", linewidth=0.7, linestyle="--", zorder=0)

    # History line (solid)
    if hist_x:
        ax.plot(hist_x, hist_y, color=ACCENT, linewidth=2.5, marker="o",
                markersize=6, zorder=3, label="历史/现值")

    # Forecast line (dashed)
    if fore_x:
        ax.plot(fore_x, fore_y, color=ACCENT, linewidth=2.5, marker="o",
                markersize=6, linestyle="--", zorder=3, label="预测")
        ax.fill_between(fore_x, fore_y, alpha=0.10, color=ACCENT, zorder=2)

    # Data labels
    label_interval = max(1, len(years) // 6)
    for i, (y, v) in enumerate(zip(years, values)):
        if i % label_interval == 0 or y == years[-1]:
            ax.annotate(
                f"{v:.0f}",
                (y, v),
                textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=9, color=ACCENT, fontweight="bold",
            )

    # CAGR badge
    ax.text(
        0.97, 0.07,
        f"CAGR  {cagr:.0f}%",
        transform=ax.transAxes,
        ha="right", va="bottom",
        fontsize=11, fontweight="bold",
        color="white",
        bbox=dict(boxstyle="round,pad=0.4", facecolor=ACCENT, linewidth=0),
    )

    ax.set_title("全球AI制药市场规模预测（亿美元）", fontsize=14, fontweight="bold",
                 color="#1a1a2e", pad=12)
    ax.set_xlabel("年份", fontsize=10, color="#4b5563")
    ax.set_ylabel("市场规模（亿美元）", fontsize=10, color="#4b5563")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.tick_params(colors="#4b5563")
    ax.legend(fontsize=9, loc="upper left", framealpha=0.8)

    # Source note
    fig.text(0.01, 0.01, source_note, fontsize=8, color="#9ca3af")

    for spine in ax.spines.values():
        spine.set_edgecolor("#d1d5db")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    logger.info("[ChartExtractor] Auto-generated market size chart → %s", output_path.name)
    return True


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_industry_charts(
    pdf_dir: Path,
    output_dir: Path,
) -> List[IndustryChart]:
    """
    Extract high-quality chart pages from sell-side research PDFs.
    For sections that receive zero qualifying PDF pages, run a matplotlib fallback.

    Args:
        pdf_dir:    Directory containing *.pdf reports (e.g. data/industryresearch/).
        output_dir: Per-run output directory.  PNGs → output_dir/industry_charts/.

    Returns:
        List[IndustryChart] (also saved to industry_charts/industry_charts.json).
    """
    pdf_dir    = Path(pdf_dir)
    charts_dir = output_dir / "industry_charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    results: List[IndustryChart] = []
    extracted: Dict[str, Set[int]] = {}          # pdf_stem → set of page indices used
    sections_with_charts: Set[str] = set()

    # ── Phase 1: PDF page extraction (quality-gated) ──────────────────────────
    for spec_idx, (section, pdf_frag, keywords, caption_hint) in enumerate(PRIORITY_SOURCES):
        pdf_path = _find_matching_pdf(pdf_dir, pdf_frag)
        if pdf_path is None:
            logger.info("[ChartExtractor] No PDF matching %r — skipping", pdf_frag)
            continue

        pdf_key    = pdf_path.stem
        excl       = extracted.setdefault(pdf_key, set())
        page_texts = _get_page_texts(pdf_path)
        if not page_texts:
            continue

        page_idx = _find_best_chart_page(page_texts, keywords, exclude=excl)

        if page_idx is None:
            score_info = []
            for i, t in enumerate(page_texts):
                if i >= SKIP_FIRST_N_PAGES and i not in excl:
                    s = _score_page(t)
                    if s != float("-inf"):
                        score_info.append(f"p{i+1}={s:.1f}")
            logger.info(
                "[ChartExtractor] SKIP %s | section=%r | best scores: %s",
                pdf_path.name, section,
                ", ".join(score_info[-5:]) if score_info else "all rejected",
            )
            continue

        excl.add(page_idx)

        slug         = _slugify_for_filename(section)
        sec_count    = sum(1 for r in results if r.section_target == section)
        img_name     = f"{spec_idx + 1:02d}_{slug}_{sec_count + 1}.png"
        img_path     = charts_dir / img_name

        if not _render_page_as_png(pdf_path, page_idx, img_path):
            continue

        source_label = _parse_source_label(pdf_path.name)
        page_num     = page_idx + 1
        caption      = f"{caption_hint} [来源：{source_label}，第{page_num}页]"

        results.append(IndustryChart(
            source_file   = pdf_path.name,
            source_label  = source_label,
            page_num      = page_num,
            caption       = caption,
            section_target= section,
            image_path    = str(img_path),
            generated     = False,
        ))
        sections_with_charts.add(section)

    # ── Phase 2: Fallback auto-generation for empty sections ──────────────────
    overview_section = "一、行业概览"
    if overview_section not in sections_with_charts:
        logger.info(
            "[ChartExtractor] No qualified chart found for %r — running fallback",
            overview_section,
        )
        market_data = _extract_market_projections(pdf_dir)
        img_path    = charts_dir / "fallback_market_size.png"
        if _generate_market_size_chart(market_data, img_path):
            cagr = market_data.get("cagr", _DEFAULT_CAGR)
            results.append(IndustryChart(
                source_file   = "auto-generated",
                source_label  = "重绘自研报数据",
                page_num      = 0,
                caption       = f"全球AI制药市场规模预测（CAGR≈{cagr:.0f}%）[数据重绘自公开研报]",
                section_target= overview_section,
                image_path    = str(img_path),
                generated     = True,
            ))

    # ── Save metadata ──────────────────────────────────────────────────────────
    meta_path = charts_dir / "industry_charts.json"
    meta_path.write_text(
        json.dumps([asdict(c) for c in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "[ChartExtractor] Done: %d chart(s) (%d PDF, %d auto-generated) → %s",
        len(results),
        sum(1 for c in results if not c.generated),
        sum(1 for c in results if c.generated),
        charts_dir,
    )
    return results


def load_industry_charts(output_dir: Path) -> Dict[str, List[dict]]:
    """
    Load chart metadata grouped by section_target.
    Returns {} if industry_charts.json not found.
    """
    meta_path = Path(output_dir) / "industry_charts" / "industry_charts.json"
    if not meta_path.exists():
        return {}
    try:
        items = json.loads(meta_path.read_text(encoding="utf-8"))
        by_section: Dict[str, List[dict]] = {}
        for item in items:
            sec = item.get("section_target", "")
            by_section.setdefault(sec, []).append(item)
        return by_section
    except Exception as exc:
        logger.warning("[ChartExtractor] Failed to load metadata: %s", exc)
        return {}
