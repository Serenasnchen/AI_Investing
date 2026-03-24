"""
html_report: Generate single-file HTML investment research reports.

Two outputs:
  report.html    — original layout (generate_html_report)
  report_v2.html — Goldman-style institutional dashboard (generate_html_report_v2)

Both read Markdown outputs from outputs/{run_id}/ and produce self-contained
HTML with inline CSS, base64-embedded charts, and a sticky sidebar TOC.
"""
import base64
import json as _json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import markdown as md_lib

logger = logging.getLogger(__name__)

# ── Markdown extensions ────────────────────────────────────────────────────────
_MD_EXTENSIONS = ["tables", "fenced_code", "nl2br", "sane_lists"]


# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = """
/* ── Reset & base ──────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --accent:      #1a56a4;
  --accent-light:#e8f0fb;
  --success:     #0d7c3d;
  --warning:     #b45309;
  --danger:      #b91c1c;
  --text:        #1a1a2e;
  --text-muted:  #4b5563;
  --border:      #d1d5db;
  --bg:          #ffffff;
  --bg-alt:      #f8fafc;
  --sidebar-w:   260px;
  --content-max: 860px;
  font-size: 16px;
}

body {
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.7;
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar / TOC ─────────────────────────────────────────────── */
#sidebar {
  position: fixed;
  top: 0; left: 0;
  width: var(--sidebar-w);
  height: 100vh;
  overflow-y: auto;
  background: var(--bg-alt);
  border-right: 1px solid var(--border);
  padding: 24px 16px;
  z-index: 100;
  scrollbar-width: thin;
}
#sidebar h2 {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 14px;
}
#sidebar nav a {
  display: block;
  color: var(--text-muted);
  text-decoration: none;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 4px;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s, color 0.15s;
}
#sidebar nav a:hover { background: var(--accent-light); color: var(--accent); }
#sidebar nav a.h3 { padding-left: 20px; font-size: 12px; }

/* ── Main content ──────────────────────────────────────────────── */
#content {
  margin-left: var(--sidebar-w);
  padding: 40px 48px 80px;
  max-width: calc(var(--sidebar-w) + var(--content-max));
  flex: 1;
}

/* ── Report header ─────────────────────────────────────────────── */
#report-header {
  border-bottom: 3px solid var(--accent);
  padding-bottom: 28px;
  margin-bottom: 40px;
}
#report-header .label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 8px;
}
#report-header h1 {
  font-size: 28px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 6px;
}
#report-header .meta {
  font-size: 13px;
  color: var(--text-muted);
}
#report-header .disclaimer {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-alt);
  border-left: 3px solid var(--border);
  padding: 8px 12px;
  border-radius: 0 4px 4px 0;
}

/* ── Sections ──────────────────────────────────────────────────── */
.section {
  margin-bottom: 52px;
}
.section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 6px;
}

/* ── Headings ──────────────────────────────────────────────────── */
h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  border-bottom: 1px solid var(--border);
  padding-bottom: 8px;
  margin: 36px 0 16px;
  scroll-margin-top: 20px;
}
h3 {
  font-size: 17px;
  font-weight: 600;
  color: var(--text);
  margin: 28px 0 10px;
  scroll-margin-top: 20px;
}
h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-muted);
  margin: 20px 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Paragraphs & lists ────────────────────────────────────────── */
p { margin-bottom: 14px; }
ul, ol { margin: 0 0 14px 22px; }
li { margin-bottom: 4px; }

/* ── Inline text ───────────────────────────────────────────────── */
strong { font-weight: 600; }
em { color: var(--text-muted); }
code {
  background: var(--bg-alt);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  font-size: 13px;
  font-family: "Cascadia Code", "Fira Code", monospace;
}

/* ── Citations ─────────────────────────────────────────────────── */
.citation {
  display: inline;
  font-size: 11.5px;
  background: var(--accent-light);
  color: var(--accent);
  border-radius: 3px;
  padding: 1px 5px;
  margin: 0 2px;
  font-style: normal;
  white-space: nowrap;
}
.citation-pubmed { background: #ecfdf5; color: var(--success); }
.citation-clintrials { background: #fff7ed; color: var(--warning); }
sup.cite-num { font-size: 10px; color: #888; vertical-align: super; font-weight: normal; }

/* ── Tables ────────────────────────────────────────────────────── */
table {
  border-collapse: collapse;
  width: 100%;
  margin: 20px 0;
  font-size: 14px;
}
th {
  background: var(--accent);
  color: white;
  padding: 9px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 12.5px;
}
td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
tr:nth-child(even) td { background: var(--bg-alt); }
tr:hover td { background: var(--accent-light); }

/* ── Conviction badges ─────────────────────────────────────────── */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.badge-high    { background: #dcfce7; color: var(--success); }
.badge-medium  { background: #fef9c3; color: #854d0e; }
.badge-low     { background: #fee2e2; color: var(--danger); }

/* ── Charts ────────────────────────────────────────────────────── */
.chart-block {
  margin: 24px 0;
  text-align: center;
}
.chart-block img {
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.chart-caption {
  margin-top: 8px;
  font-size: 12.5px;
  color: var(--text-muted);
  font-style: italic;
}

/* ── Callout / warning box ─────────────────────────────────────── */
.callout {
  border-left: 4px solid var(--danger);
  background: #fef2f2;
  padding: 14px 18px;
  border-radius: 0 6px 6px 0;
  margin: 20px 0;
  font-size: 14px;
}
.callout-title {
  font-weight: 700;
  color: var(--danger);
  margin-bottom: 6px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.callout-warning { border-left-color: var(--warning); background: #fffbeb; }
.callout-warning .callout-title { color: var(--warning); }

/* ── Horizontal rule ───────────────────────────────────────────── */
hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }

/* ── Footer ────────────────────────────────────────────────────── */
#footer {
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

/* ── Industry research charts block ────────────────────────────── */
.industry-charts-block {
  margin: 28px 0 8px;
  border-top: 2px solid var(--accent-light);
  padding-top: 16px;
}
.industry-charts-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 14px;
}
.industry-charts-block .chart-block {
  margin-bottom: 24px;
}

/* ── Print ─────────────────────────────────────────────────────── */
@media print {
  #sidebar { display: none; }
  #content { margin-left: 0; padding: 20px; }
  body { display: block; }
}

/* ── Responsive ────────────────────────────────────────────────── */
@media (max-width: 768px) {
  #sidebar { display: none; }
  #content { margin-left: 0; padding: 20px 16px; }
}
"""

# ── JS (smooth scroll + active TOC highlight) ──────────────────────────────────
_JS = """
(function () {
  // Smooth scroll for TOC links
  document.querySelectorAll('#sidebar nav a').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) { e.preventDefault(); el.scrollIntoView({behavior:'smooth', block:'start'}); }
    });
  });

  // Active TOC item on scroll
  const headings = Array.from(document.querySelectorAll('h2[id], h3[id]'));
  const links    = Array.from(document.querySelectorAll('#sidebar nav a'));
  function onScroll() {
    let active = null;
    for (const h of headings) {
      if (h.getBoundingClientRect().top <= 60) active = h.id;
    }
    links.forEach(a => {
      a.style.color = '';
      a.style.background = '';
      if (active && a.getAttribute('href') === '#' + active) {
        a.style.background = 'var(--accent-light)';
        a.style.color = 'var(--accent)';
      }
    });
  }
  window.addEventListener('scroll', onScroll, {passive: true});
})();
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert heading text to a URL-safe anchor id."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text


def _encode_image(path: Path) -> Optional[str]:
    """Return a base64 data URI for a PNG file, or None on error."""
    try:
        data = path.read_bytes()
        b64  = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:
        logger.warning("Could not encode image %s: %s", path.name, exc)
        return None


def _md_to_html(text: str) -> str:
    """Convert Markdown to HTML with standard extensions."""
    return md_lib.markdown(text, extensions=_MD_EXTENSIONS)


def _stylize_citations(html: str) -> str:
    """
    Wrap citation tokens in styled <span> elements:
      [paper: ...]         → <span class="citation">📄 ...</span>
      [PubMed: PMID]       → <span class="citation citation-pubmed">🔬 PubMed: PMID</span>
      [ClinicalTrials: ID] → <span class="citation citation-clintrials">🏥 NCT: ID</span>
    """
    # Paper citations
    html = re.sub(
        r'\[paper:\s*([^\]]+)\]',
        lambda m: f'<span class="citation">📄 {m.group(1).strip()}</span>',
        html,
    )
    # PubMed citations
    html = re.sub(
        r'\[PubMed:\s*([^\]]+)\]',
        lambda m: f'<span class="citation citation-pubmed">🔬 PubMed: {m.group(1).strip()}</span>',
        html,
    )
    # ClinicalTrials citations
    html = re.sub(
        r'\[ClinicalTrials:\s*([^\]]+)\]',
        lambda m: f'<span class="citation citation-clintrials">🏥 NCT: {m.group(1).strip()}</span>',
        html,
    )
    # Numbered citations [N] produced by _number_citations()
    html = re.sub(
        r'\[(\d+)\]',
        lambda m: f'<sup class="cite-num">[{m.group(1)}]</sup>',
        html,
    )
    return html


def _conviction_badge(text: str) -> str:
    """Replace conviction labels in HTML with styled badges."""
    def _replace(m: re.Match) -> str:
        val = m.group(1).upper()
        css = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low"}.get(val, "badge-medium")
        return f'<span class="badge {css}">{val}</span>'
    return re.sub(r'\b(HIGH|MEDIUM|LOW)\b', _replace, text)


def _extract_title_and_date(md_text: str) -> Tuple[str, str]:
    """Pull # title and generated date from report markdown.

    Supports two formats:
      - Legacy English: *Generated: 2025-01-01 12:00*
      - New Chinese:    *生成时间：2025-01-01 12:00　｜　AI投研系统*
    """
    title = "Investment Research Report"
    date  = ""
    for line in md_text.splitlines():
        if line.startswith("# ") and title == "Investment Research Report":
            title = line[2:].strip()
        # English format
        m = re.search(r'\*Generated:\s*([^*|]+)\*', line)
        if m:
            date = m.group(1).strip()
        # Chinese format: *生成时间：DATE　｜　...*
        m2 = re.search(r'\*生成时间[：:]\s*([^*|｜]+)', line)
        if m2:
            date = m2.group(1).strip()
        if title != "Investment Research Report" and date:
            break
    return title, date


def _extract_sections(md_text: str) -> List[Tuple[str, str]]:
    """
    Split markdown into (heading, body) pairs at every ## heading.
    Returns list of (heading_text, body_markdown).
    """
    sections: List[Tuple[str, str]] = []
    current_heading = ""
    current_lines: List[str] = []

    for line in md_text.splitlines():
        if line.startswith("## "):
            if current_heading or current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading or current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections


def _build_toc(sections_with_ids: List[Tuple[str, str, str]]) -> str:
    """
    Build sidebar TOC HTML from (heading, anchor_id, body_html) tuples.
    Also picks up h3 anchors embedded inside body_html.
    """
    items = []
    for heading, anchor_id, body_html in sections_with_ids:
        if not heading:
            continue
        items.append(f'<a href="#{anchor_id}">{heading}</a>')
        # Find h3 headings inside the body
        for m in re.finditer(r'<h3 id="([^"]+)">([^<]+)</h3>', body_html):
            h3_id, h3_text = m.group(1), m.group(2)
            items.append(f'<a class="h3" href="#{h3_id}">{h3_text}</a>')
    return "\n".join(items)


def _add_h3_anchors(html: str) -> str:
    """Add id attributes to every <h3> tag based on its text content."""
    def replacer(m: re.Match) -> str:
        inner = re.sub(r'<[^>]+>', '', m.group(1))  # strip inner tags for slug
        anchor = _slugify(inner)
        return f'<h3 id="{anchor}">{m.group(1)}</h3>'
    return re.sub(r'<h3>(.*?)</h3>', replacer, html)


def _charts_block(charts_dir: Path) -> str:
    """Return HTML for all charts found in charts/, or empty string."""
    if not charts_dir.exists():
        return ""
    pngs = sorted(charts_dir.glob("*.png"))
    if not pngs:
        return ""

    captions = {
        "sourcing_ranking": "图1 — 公司筛选评分排名（总分/25分）",
    }

    blocks = []
    for png in pngs:
        data_uri = _encode_image(png)
        if not data_uri:
            continue
        stem = png.stem
        caption = captions.get(stem, stem.replace("_", " ").title())
        blocks.append(
            f'<div class="chart-block">'
            f'<img src="{data_uri}" alt="{caption}">'
            f'<div class="chart-caption">{caption}</div>'
            f'</div>'
        )
    return "\n".join(blocks)


def _wrap_validation_notes(html_body: str) -> str:
    """Wrap validation-note items in callout divs.

    Handles two formats:
      - Legacy English: paragraphs starting with "CRITICAL CAVEATS"
      - New Chinese:    paragraphs/list items starting with "【待核实】"
    """
    # Legacy English: CRITICAL CAVEATS paragraph
    html_body = re.sub(
        r'(<p>)(CRITICAL CAVEATS[^<]*</p>)',
        r'<div class="callout"><div class="callout-title">⚠ Critical Caveats</div>\1\2</div>',
        html_body,
        flags=re.DOTALL,
    )
    # New Chinese: items starting with 【待核实】
    html_body = re.sub(
        r'(<(?:p|li)>)(【待核实】[^<]*</(?:p|li)>)',
        r'<div class="callout callout-warning"><div class="callout-title">⚠ 待核实</div>\1\2</div>',
        html_body,
        flags=re.DOTALL,
    )
    return html_body


def _render_industry_charts_html(charts: List[dict]) -> str:
    """
    Build an HTML block for a list of industry-research chart dicts.
    Each dict must have 'image_path' and 'caption' keys (from IndustryChart.asdict()).
    """
    parts = [
        '<div class="industry-charts-block">',
        '<div class="industry-charts-label">&#128202; 研报图表参考</div>',
    ]
    for chart in charts:
        img_path = Path(chart.get("image_path") or "")
        if not img_path.exists():
            continue
        data_uri = _encode_image(img_path)
        if not data_uri:
            continue
        caption = chart.get("caption", img_path.stem)
        parts.append(
            f'<div class="chart-block">'
            f'<img src="{data_uri}" alt="{caption}">'
            f'<div class="chart-caption">{caption}</div>'
            f'</div>'
        )
    parts.append("</div>")
    # Return empty string if no images were embedded
    if len(parts) == 3:  # only wrapper + label + closing div
        return ""
    return "\n".join(parts)


# ── Main public function ───────────────────────────────────────────────────────

def generate_html_report(output_dir: Path) -> Path:
    """
    Generate a single-file HTML investment research report from Markdown outputs.

    Args:
        output_dir: Path to the run's output directory (outputs/{run_id}/).

    Returns:
        Path to the saved report.html.
    """
    output_dir = Path(output_dir)

    # ── 1. Read source files ───────────────────────────────────────────────────
    main_md_path = output_dir / "final_report.md"
    if not main_md_path.exists():
        raise FileNotFoundError(f"final_report.md not found in {output_dir}")

    main_md = main_md_path.read_text(encoding="utf-8")
    title, gen_date = _extract_title_and_date(main_md)

    memo_md        = (output_dir / "memos.md").read_text(encoding="utf-8") if (output_dir / "memos.md").exists() else ""
    public_mkt_md  = (output_dir / "public_market.md").read_text(encoding="utf-8") if (output_dir / "public_market.md").exists() else ""

    # ── 2. Extract sections from main report ───────────────────────────────────
    raw_sections = _extract_sections(main_md)
    # Skip the preamble section (before first ##) and lines like *Generated:...*
    processed_sections: List[Tuple[str, str, str]] = []  # (heading, anchor_id, body_html)

    for heading, body_md in raw_sections:
        if not heading:
            continue  # skip preamble / blank
        anchor_id = _slugify(heading)
        raw_html  = _md_to_html(body_md)
        raw_html  = _add_h3_anchors(raw_html)
        raw_html  = _stylize_citations(raw_html)
        raw_html  = _conviction_badge(raw_html)
        if heading in ("Validation Notes", "数据质量说明"):
            raw_html = _wrap_validation_notes(raw_html)
        processed_sections.append((heading, anchor_id, raw_html))

    # ── 3. Sourcing ranking charts ─────────────────────────────────────────────
    charts_html = _charts_block(output_dir / "charts")

    # ── 3b. Industry research charts (per-section) ─────────────────────────────
    try:
        from src.reporting.industry_chart_extractor import load_industry_charts
        industry_charts_by_section = load_industry_charts(output_dir)
    except Exception as _ic_exc:
        logger.warning("Could not load industry charts: %s", _ic_exc)
        industry_charts_by_section = {}

    # ── 4. Appendix sections ───────────────────────────────────────────────────
    appendix_sections: List[Tuple[str, str, str]] = []
    if memo_md:
        memo_html = _md_to_html(memo_md)
        memo_html = _add_h3_anchors(memo_html)
        memo_html = _stylize_citations(memo_html)
        memo_html = _conviction_badge(memo_html)
        appendix_sections.append(("Appendix A — Diligence Memos", "appendix-a-diligence-memos", memo_html))

    if public_mkt_md:
        pm_html = _md_to_html(public_mkt_md)
        pm_html = _add_h3_anchors(pm_html)
        pm_html = _stylize_citations(pm_html)
        pm_html = _conviction_badge(pm_html)
        appendix_sections.append(("Appendix B — Public Market Detail", "appendix-b-public-market-detail", pm_html))

    all_sections = processed_sections + appendix_sections

    # ── 5. TOC ─────────────────────────────────────────────────────────────────
    toc_html = _build_toc(all_sections)

    # ── 6. Body sections HTML ─────────────────────────────────────────────────
    body_parts = []

    # Insert sourcing ranking chart after the sourcing/screening section
    chart_inserted = False
    for heading, anchor_id, body_html in all_sections:
        h2_tag = f'<h2 id="{anchor_id}">{heading}</h2>'
        body_parts.append(h2_tag)
        body_parts.append(body_html)

        # Insert sourcing ranking chart after the sourcing section
        if not chart_inserted and charts_html and heading in (
            # New Chinese section names
            "一、行业概览",
            "2.1 Sourcing：公司筛选与市场地图",
            # Legacy English section names (backward compat)
            "Company Diligence Highlights", "Private Market Overview", "Executive Summary",
        ):
            body_parts.append(charts_html)
            chart_inserted = True

        # Insert industry research charts for this section (after body text)
        sec_charts = industry_charts_by_section.get(heading, [])
        if sec_charts:
            ic_html = _render_industry_charts_html(sec_charts)
            if ic_html:
                body_parts.append(ic_html)

    # If sourcing chart never inserted (sections have different names), put before appendix
    if not chart_inserted and charts_html:
        insert_at = len(processed_sections) * 2  # after all main sections
        body_parts.insert(insert_at, charts_html)

    body_html_full = "\n".join(body_parts)

    # ── 7. Assemble full HTML ──────────────────────────────────────────────────
    # Strip known suffixes/prefixes for both Chinese and English title formats
    sector_label = (
        title
        .replace("Investment Research Report:", "")
        .replace("行业深度研究报告", "")
        .strip()
    ) or title
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{_CSS}</style>
</head>
<body>

<!-- ── Sidebar ──────────────────────────────────────── -->
<aside id="sidebar">
  <h2>Contents</h2>
  <nav>
    {toc_html}
  </nav>
</aside>

<!-- ── Main content ─────────────────────────────────── -->
<main id="content">

  <div id="report-header">
    <div class="label">Investment Research Report</div>
    <h1>{sector_label if sector_label else title}</h1>
    <div class="meta">
      Generated: {gen_date or now_str}
      &nbsp;·&nbsp; AI-Driven Research Pipeline
      &nbsp;·&nbsp; Powered by Claude
    </div>
    <div class="disclaimer">
      <strong>Disclaimer:</strong> This report is generated by an AI research pipeline for academic and educational purposes only.
      It does not constitute investment advice. All data should be independently verified before use.
    </div>
  </div>

  {body_html_full}

  <div id="footer">
    Generated {now_str} by AI Investing Research Pipeline &nbsp;·&nbsp;
    For academic use only — not investment advice
  </div>

</main>

<script>{_JS}</script>
</body>
</html>"""

    # ── 8. Save ────────────────────────────────────────────────────────────────
    out_path = output_dir / "report.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("[html_report] Saved → %s  (%d KB)", out_path.name, len(html) // 1024)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# v2: Goldman-Style Institutional Research Dashboard
# ══════════════════════════════════════════════════════════════════════════════

_CSS_V2 = """
/* ── Goldman-Style Research Dashboard ────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --navy:         #0a2342;
  --navy-mid:     #0f3460;
  --navy-light:   #1a4a7a;
  --gold:         #c9a84c;
  --gold-light:   #f5e9c0;
  --blue:         #3a5a8c;
  --blue-light:   #dce8f5;
  --text:         #1a2332;
  --text-body:    #2d3748;
  --text-muted:   #64748b;
  --text-light:   #94a3b8;
  --text-cite:    #8fa3b8;
  --bg-page:      #eff1f5;
  --bg-card:      #ffffff;
  --bg-alt:       #f8fafc;
  --risk-red:     #7f1d1d;
  --risk-bg:      #fff5f5;
  --risk-border:  #fca5a5;
  --border:       #e2e8f0;
  --border-dark:  #cbd5e1;
  --sidebar-w:    220px;
  font-size: 15px;
}

body {
  font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  color: var(--text-body);
  background: var(--bg-page);
  line-height: 1.65;
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ──────────────────────────────────────────────── */
#sidebar {
  position: fixed;
  top: 0; left: 0;
  width: var(--sidebar-w);
  height: 100vh;
  overflow-y: auto;
  background: var(--navy);
  z-index: 100;
  scrollbar-width: thin;
  scrollbar-color: var(--navy-mid) var(--navy);
  display: flex;
  flex-direction: column;
}
.sidebar-brand {
  padding: 20px 18px 14px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--gold);
  border-bottom: 1px solid var(--navy-mid);
}
.sidebar-label {
  padding: 14px 18px 6px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.30);
}
#sidebar nav { flex: 1; padding: 0 10px 16px; }
#sidebar nav a {
  display: block;
  color: rgba(255,255,255,0.58);
  text-decoration: none;
  font-size: 12.5px;
  padding: 5px 8px;
  border-radius: 4px;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s, color 0.15s;
  border-left: 2px solid transparent;
}
#sidebar nav a:hover { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.9); }
#sidebar nav a.active { color: var(--gold); border-left-color: var(--gold); background: rgba(201,168,76,0.08); }
#sidebar nav a.h3 { padding-left: 18px; font-size: 11.5px; color: rgba(255,255,255,0.38); }
.sidebar-footer {
  padding: 12px 18px;
  font-size: 10px;
  color: rgba(255,255,255,0.22);
  border-top: 1px solid var(--navy-mid);
  letter-spacing: 0.04em;
}

/* ── Main content ─────────────────────────────────────────── */
#content { margin-left: var(--sidebar-w); padding: 0 0 80px; flex: 1; min-width: 0; }

/* ── Hero banner ─────────────────────────────────────────── */
.hero {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-mid) 60%, var(--navy-light) 100%);
  color: white;
  padding: 40px 52px 36px;
  border-bottom: 3px solid var(--gold);
}
.hero-eyebrow {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 10px;
}
.hero h1 {
  font-size: 30px;
  font-weight: 800;
  color: white;
  margin-bottom: 8px;
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.hero-meta { font-size: 12.5px; color: rgba(255,255,255,0.50); margin-bottom: 28px; }

/* ── KPI row ──────────────────────────────────────────────── */
.kpi-row { display: flex; gap: 14px; flex-wrap: wrap; }
.kpi-card {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.13);
  border-radius: 8px;
  padding: 14px 18px;
  min-width: 110px;
  flex: 1;
  text-align: center;
  transition: background 0.15s;
}
.kpi-card:hover { background: rgba(255,255,255,0.12); }
.kpi-number { font-size: 26px; font-weight: 800; color: var(--gold); line-height: 1.1; letter-spacing: -0.02em; }
.kpi-label { font-size: 10.5px; color: rgba(255,255,255,0.50); margin-top: 5px; letter-spacing: 0.06em; text-transform: uppercase; }

/* ── Disclaimer strip ────────────────────────────────────── */
.disclaimer {
  background: #fefce8;
  border-left: 3px solid #d97706;
  padding: 10px 52px;
  font-size: 12px;
  color: #78350f;
  line-height: 1.5;
}

/* ── Content wrapper ─────────────────────────────────────── */
.content-wrapper { padding: 28px 52px; }

/* ── Section cards ────────────────────────────────────────── */
.report-section {
  background: var(--bg-card);
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 8px rgba(0,0,0,0.04);
  margin-bottom: 24px;
  overflow: hidden;
  scroll-margin-top: 20px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 28px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-alt);
}
.section-num {
  font-size: 11px;
  font-weight: 700;
  color: white;
  background: var(--navy);
  width: 26px; height: 26px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  letter-spacing: 0;
}
.section-header h2 {
  font-size: 17px;
  font-weight: 700;
  color: var(--navy);
  margin: 0; padding: 0; border: none;
}
.section-body-wrap { padding: 22px 28px; }

/* ── Thesis card ──────────────────────────────────────────── */
.thesis-card {
  background: linear-gradient(135deg, #f0f6ff 0%, #e8f2fd 100%);
  border-left: 3px solid var(--blue);
  border-radius: 0 6px 6px 0;
  padding: 12px 18px;
  margin-bottom: 18px;
}
.thesis-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--blue);
  margin-bottom: 5px;
}
.thesis-text { font-size: 14px; font-weight: 600; color: var(--text); line-height: 1.5; }

/* ── Inner headings ───────────────────────────────────────── */
.section-body-wrap h2 {
  font-size: 16px; font-weight: 700; color: var(--navy);
  border-bottom: 1px solid var(--border); padding-bottom: 5px;
  margin: 26px 0 10px; scroll-margin-top: 20px;
}
.section-body-wrap h3 { font-size: 14.5px; font-weight: 600; color: var(--text); margin: 20px 0 8px; scroll-margin-top: 20px; }
.section-body-wrap h4 { font-size: 12.5px; font-weight: 600; color: var(--text-muted); margin: 14px 0 5px; text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Body text ────────────────────────────────────────────── */
.section-body-wrap p { margin-bottom: 11px; font-size: 13.5px; }
.section-body-wrap ul, .section-body-wrap ol { margin: 0 0 11px 20px; }
.section-body-wrap li { margin-bottom: 4px; font-size: 13.5px; }
strong { font-weight: 600; }
em { color: var(--text-muted); }
code {
  background: var(--bg-alt); border: 1px solid var(--border);
  border-radius: 3px; padding: 1px 5px;
  font-size: 12.5px; font-family: "Cascadia Code", "Fira Code", monospace;
}
hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }

/* ── Tables ─────────────────────────────────────────────────── */
.section-body-wrap table {
  border-collapse: collapse; width: 100%;
  margin: 14px 0; font-size: 12.5px;
  border-radius: 6px; overflow: hidden;
}
.section-body-wrap th {
  background: var(--navy); color: white;
  padding: 8px 12px; text-align: left;
  font-weight: 600; font-size: 11.5px; letter-spacing: 0.03em;
}
.section-body-wrap td { padding: 7px 12px; border-bottom: 1px solid var(--border); color: var(--text-body); }
.section-body-wrap tr:nth-child(even) td { background: var(--bg-alt); }
.section-body-wrap tr:hover td { background: var(--blue-light); }

/* ── Citations ─────────────────────────────────────────────── */
.citation {
  display: inline; font-size: 10.5px;
  background: rgba(58,90,140,0.08); color: var(--text-cite);
  border-radius: 3px; padding: 1px 4px; margin: 0 2px;
  font-style: normal; white-space: nowrap;
}
.citation-pubmed { background: rgba(16,185,129,0.08); color: #059669; }
.citation-clintrials { background: rgba(245,158,11,0.08); color: #d97706; }
sup.cite-num { font-size: 10px; color: #8a9bbf; vertical-align: super; font-weight: normal; }

/* ── Conviction badges ─────────────────────────────────────── */
.badge {
  display: inline-block; padding: 2px 7px; border-radius: 3px;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
}
.badge-high   { background: #dcfce7; color: #15803d; }
.badge-medium { background: #fef9c3; color: #92400e; }
.badge-low    { background: #fee2e2; color: #b91c1c; }

/* ── Chart cards ───────────────────────────────────────────── */
.chart-card {
  border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; margin: 18px 0;
  background: var(--bg-card); box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.chart-card-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 16px; background: var(--bg-alt); border-bottom: 1px solid var(--border);
}
.chart-card-title { font-size: 12px; font-weight: 600; color: var(--text); }
.chart-card-source { font-size: 11px; color: var(--text-cite); letter-spacing: 0.02em; }
.chart-card img { display: block; width: 100%; height: auto; }
.chart-card-caption { padding: 8px 16px; font-size: 11px; color: var(--text-muted); font-style: italic; border-top: 1px solid var(--border); }

/* ── Industry charts block ─────────────────────────────────── */
.industry-charts-block { margin: 22px 0 0; padding: 18px 0 0; border-top: 1px dashed var(--border-dark); }
.industry-charts-label { font-size: 10.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--blue); margin-bottom: 12px; }
/* ── Manual graph blocks ───────────────────────────────────── */
/* Outer wrapper — always centred, never full-bleed */
.manual-charts-block { margin: 24px 0; display: flex; flex-direction: column; align-items: center; gap: 0; }

/* Single image: card capped at 62% of the content column */
.manual-charts-block.single-chart  { align-items: center; }
.manual-charts-block.single-chart  .mg-card { max-width: 62%; width: 62%; }

/* Vertical stack (biz_model): two images stacked, each ~72%, centred */
.manual-charts-block.vertical-stack { flex-direction: column; align-items: center; gap: 20px; }
.manual-charts-block.vertical-stack .mg-card { max-width: 72%; width: 72%; }

/* Two images: side-by-side grid, each card ~46% */
.manual-charts-block.two-chart-grid {
  flex-direction: row; flex-wrap: wrap;
  justify-content: center; gap: 16px; align-items: flex-start;
}
.manual-charts-block.two-chart-grid .mg-card { width: 46%; min-width: 200px; flex: 0 1 46%; }

/* Three-or-more: responsive 2-column grid */
.manual-charts-block.multi-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px; width: 92%; max-width: 780px;
}

/* Individual card */
.mg-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  overflow: hidden;
  display: flex; flex-direction: column; align-items: stretch;
}
.mg-card-header {
  padding: 7px 14px; background: var(--bg-alt);
  border-bottom: 1px solid var(--border);
  font-size: 11.5px; font-weight: 600; color: var(--text);
  letter-spacing: 0.01em;
}
.mg-card-img-wrap {
  padding: 10px 14px; display: flex; justify-content: center; align-items: center;
  background: var(--bg-card);
}
.mg-card-img-wrap img {
  display: block; max-width: 100%; height: auto;
  border-radius: 4px;
}
.mg-card-caption {
  padding: 5px 14px 8px; font-size: 10px; color: #8a9bbf;
  text-align: center; font-style: italic; line-height: 1.4;
  border-top: 1px solid var(--border);
}

/* ── Risk cards grid ───────────────────────────────────────── */
.risk-grid {
  display: grid; grid-template-columns: repeat(2, 1fr);
  gap: 14px; margin: 14px 0 20px;
}
.risk-card {
  background: var(--risk-bg); border: 1px solid var(--risk-border);
  border-left: 3px solid var(--risk-red); border-radius: 6px; padding: 16px 18px;
}
.risk-card-badge {
  display: inline-block; font-size: 9.5px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--risk-red); background: rgba(127,29,29,0.07);
  border-radius: 3px; padding: 2px 7px; margin-bottom: 8px;
}
.risk-card h4 { font-size: 13px; font-weight: 700; color: var(--risk-red); margin-bottom: 8px; text-transform: none; letter-spacing: 0; }
.risk-card p, .risk-card li { font-size: 12px; color: #4b1c1c; line-height: 1.55; margin-bottom: 3px; }
.risk-card ul { margin-left: 14px; }

/* ── Callout / warning ─────────────────────────────────────── */
.callout {
  border-left: 3px solid #f59e0b; background: #fffbeb;
  padding: 12px 16px; border-radius: 0 6px 6px 0; margin: 14px 0; font-size: 13px;
}
.callout-title { font-weight: 700; color: #92400e; margin-bottom: 5px; font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.05em; }
.callout-warning { border-left-color: #f59e0b; background: #fffbeb; }
.callout-warning .callout-title { color: #92400e; }

/* ── Footer ────────────────────────────────────────────────── */
.report-footer {
  margin-top: 40px; padding: 18px 52px;
  border-top: 1px solid var(--border);
  font-size: 11.5px; color: var(--text-light);
  display: flex; justify-content: space-between; align-items: center;
}

/* ── Print ─────────────────────────────────────────────────── */
@media print {
  #sidebar { display: none; }
  #content { margin-left: 0; }
  .hero { background: white !important; color: black !important; }
  .report-section { box-shadow: none; border: 1px solid #ddd; }
}

/* ── Responsive ────────────────────────────────────────────── */
@media (max-width: 900px) {
  #sidebar { display: none; }
  #content { margin-left: 0; }
  .hero { padding: 28px 24px 24px; }
  .content-wrapper { padding: 20px 24px; }
  .disclaimer { padding: 10px 24px; }
  .report-footer { padding: 16px 24px; flex-direction: column; gap: 8px; text-align: center; }
  .risk-grid { grid-template-columns: 1fr; }
}
"""

_JS_V2 = """
(function () {
  document.querySelectorAll('#sidebar nav a').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) { e.preventDefault(); el.scrollIntoView({behavior:'smooth', block:'start'}); }
    });
  });

  const sections = Array.from(document.querySelectorAll('.report-section[id]'));
  const links    = Array.from(document.querySelectorAll('#sidebar nav a'));
  function onScroll() {
    let active = null;
    for (const s of sections) {
      if (s.getBoundingClientRect().top <= 80) active = s.id;
    }
    links.forEach(a => {
      a.classList.remove('active');
      if (active && a.getAttribute('href') === '#' + active) a.classList.add('active');
    });
  }
  window.addEventListener('scroll', onScroll, {passive: true});
  onScroll();
})();
"""


# ── v2 helper functions ────────────────────────────────────────────────────────

def _extract_kpi_data(output_dir: Path, processed_dir: Optional[Path] = None) -> dict:
    """Extract KPI counts from processed JSON files, with fallback navigation."""
    kpis: dict = {"private_count": 0, "public_count": 0, "catalyst_count": 0}

    if processed_dir is None:
        run_id = output_dir.name
        candidate = output_dir.parent.parent / "data" / "processed" / run_id
        if candidate.exists():
            processed_dir = candidate

    if processed_dir is None or not processed_dir.exists():
        return kpis

    for fname, key in [
        ("startup_profiles.json", "private_count"),
        ("public_market_profiles.json", "public_count"),
        ("catalysts.json", "catalyst_count"),
    ]:
        fp = processed_dir / fname
        if fp.exists():
            try:
                data = _json.loads(fp.read_text(encoding="utf-8"))
                kpis[key] = len(data) if isinstance(data, list) else 0
            except Exception:
                pass

    return kpis


def _extract_section_thesis(body_md: str) -> str:
    """Return the first substantive sentence from a section's markdown body."""
    for line in body_md.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip markdown headings, dividers
        if line.startswith(("#", "---", "===")):
            continue
        # Skip subsection bold headers like **（一）...**
        if re.match(r"^\*\*[（(【]", line):
            continue
        # Skip bullet list sub-headers like - **核心技术**
        if re.match(r"^[-*]\s*\*\*", line):
            continue
        # Strip markdown formatting
        clean = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line)
        clean = re.sub(r"\[([^\]]+)\](?:\([^)]+\))?", r"\1", clean)
        clean = re.sub(r"\[来源：[^\]]+\]", "", clean).strip()
        if len(clean) < 15:
            continue
        # Return up to the first sentence break
        m = re.search(r"[。！？]", clean)
        if m:
            return clean[: m.start() + 1]
        # Return first 120 chars
        return clean[:120] + ("..." if len(clean) > 120 else "")
    return ""


def _parse_risk_cards(risk_body_md: str) -> List[dict]:
    """
    Parse the risk_factors markdown into structured risk cards.

    Expects sections headed by **XXX风险** with bullet-point content.
    Returns a list of dicts: {badge, title, bullets}.
    """
    RISK_TYPES = ["技术风险", "临床风险", "商业化风险", "政策与监管风险"]
    BADGES = {
        "技术风险": "技术",
        "临床风险": "临床",
        "商业化风险": "商业化",
        "政策与监管风险": "监管",
    }

    cards: List[dict] = []
    current_type: Optional[str] = None
    current_bullets: List[str] = []

    for line in risk_body_md.splitlines():
        stripped = line.strip()
        found_type = None
        for rt in RISK_TYPES:
            if rt in stripped and stripped.startswith("**"):
                found_type = rt
                break
        if found_type:
            if current_type and current_bullets:
                cards.append({"badge": BADGES.get(current_type, current_type[:2]), "title": current_type, "bullets": current_bullets})
            current_type = found_type
            current_bullets = []
        elif current_type and re.match(r"^[-•*]\s", stripped):
            bullet = re.sub(r"^[-•*]\s*", "", stripped)
            bullet = re.sub(r"\[来源：[^\]]+\]", "", bullet).strip()
            if bullet:
                current_bullets.append(bullet)

    if current_type and current_bullets:
        cards.append({"badge": BADGES.get(current_type, current_type[:2]), "title": current_type, "bullets": current_bullets})

    return cards


def _build_kpi_cards_html(kpis: dict, run_date: str) -> str:
    """Build the KPI card row HTML for the hero section."""
    date_short = run_date[:10] if run_date else "—"
    cards_data = [
        (str(kpis.get("private_count") or "—"), "重点私有公司"),
        (str(kpis.get("public_count") or "—"), "上市标的"),
        (str(kpis.get("catalyst_count") or "—"), "催化剂事件"),
        (date_short, "报告日期"),
    ]
    parts = []
    for number, label in cards_data:
        parts.append(
            f'<div class="kpi-card">'
            f'<div class="kpi-number">{number}</div>'
            f'<div class="kpi-label">{label}</div>'
            f"</div>"
        )
    return "\n".join(parts)


def _charts_block_v2(charts_dir: Path) -> str:
    """Return chart-card HTML for PNG charts in charts/, or empty string."""
    if not charts_dir.exists():
        return ""
    pngs = sorted(charts_dir.glob("*.png"))
    if not pngs:
        return ""
    captions = {"sourcing_ranking": "公司筛选评分排名（总分/25分）"}
    blocks = []
    for png in pngs:
        data_uri = _encode_image(png)
        if not data_uri:
            continue
        stem = png.stem
        caption = captions.get(stem, stem.replace("_", " ").title())
        blocks.append(
            f'<div class="chart-card" style="max-width:50%;margin:16px auto;">'
            f'<div class="chart-card-header">'
            f'<div class="chart-card-title">{caption}</div>'
            f'<div class="chart-card-source">AI投研系统生成</div>'
            f"</div>"
            f'<img src="{data_uri}" alt="{caption}">'
            f"</div>"
        )
    return "\n".join(blocks)


def _render_industry_charts_html_v2(charts: List[dict]) -> str:
    """Build chart-card HTML for industry-research chart dicts."""
    parts = [
        '<div class="industry-charts-block">',
        '<div class="industry-charts-label">&#128202; 研报图表参考</div>',
    ]
    has_any = False
    for chart in charts:
        img_path = Path(chart.get("image_path") or "")
        if not img_path.exists():
            continue
        data_uri = _encode_image(img_path)
        if not data_uri:
            continue
        has_any = True
        caption = chart.get("caption", img_path.stem)
        source = chart.get("source_file", "")
        source_label = ""
        if source:
            m = re.match(r"(\d{4}-\d{2}-\d{2})_([^_]+)", source)
            source_label = f"{m.group(2)} {m.group(1)}" if m else source[:30]

        is_fallback = "fallback" in img_path.stem.lower()
        card_style = ' style="max-width:50%;margin:16px auto;"' if is_fallback else ''
        parts.append(f'<div class="chart-card"{card_style}>')
        parts.append('<div class="chart-card-header">')
        parts.append(f'<div class="chart-card-title">{caption}</div>')
        if source_label:
            parts.append(f'<div class="chart-card-source">来源：{source_label}</div>')
        parts.append("</div>")
        parts.append(f'<img src="{data_uri}" alt="{caption}">')
        parts.append("</div>")

    parts.append("</div>")
    if not has_any:
        return ""
    return "\n".join(parts)


def _build_risk_cards_html(risk_cards: List[dict]) -> str:
    """Render a 2-column risk grid from parsed risk card dicts."""
    parts = ['<div class="risk-grid">']
    for rc in risk_cards:
        bullets_html = "".join(f"<li>{b}</li>" for b in rc["bullets"])
        parts.append(
            f'<div class="risk-card">'
            f'<div class="risk-card-badge">{rc["badge"]}</div>'
            f'<h4>{rc["title"]}</h4>'
            f"<ul>{bullets_html}</ul>"
            f"</div>"
        )
    parts.append("</div>")
    return "\n".join(parts)


# ── Manual graph injection ─────────────────────────────────────────────────────

# subsection text patterns → section_key (for within-body injection)
_MANUAL_SUB_PATTERNS = [
    (re.compile(r"AI在制药中的角色|ai在制药中的角色", re.IGNORECASE), "role"),
    (re.compile(r"市场规模与增速"),                                   "market_size"),
    (re.compile(r"Sourcing|公司筛选与市场地图"),                       "sourcing_map"),
    (re.compile(r"竞争格局"),                                         "competition"),
    (re.compile(r"商业模式"),                                         "biz_model"),
]


def _manual_graph_cards_html(entries: list, section_key: str = "") -> str:
    """
    Build responsive chart-card HTML for manual graph entries.
    Layout:
      biz_model (special) → vertical stack, each card max-width 72%, centred
      1 image  → single-chart  (max-width: 62% of content column, centred)
      2 images → two-chart-grid (side-by-side, each ~46%)
      3+       → multi-chart-grid (2-column CSS grid)
    """
    valid: list = []
    for entry in entries:
        data_uri = _encode_image(entry.path)
        if data_uri:
            valid.append((entry, data_uri))

    if not valid:
        return ""

    # biz_model / sourcing_map: always vertical regardless of count
    if section_key in ("biz_model", "sourcing_map"):
        layout_cls = "vertical-stack"
    elif len(valid) == 1:
        layout_cls = "single-chart"
    elif len(valid) == 2:
        layout_cls = "two-chart-grid"
    else:
        layout_cls = "multi-chart-grid"

    parts = [f'<div class="manual-charts-block {layout_cls}">']
    for entry, data_uri in valid:
        parts.append(
            f'<div class="mg-card">'
            f'<div class="mg-card-img-wrap">'
            f'<img src="{data_uri}" alt="">'
            f'</div>'
            f'</div>'
        )
    parts.append('</div>')
    return "\n".join(parts)


def _inject_manual_graphs_into_body(body_html: str, graphs_by_key: dict) -> str:
    """
    Scan body_html for h3/h4/strong subsection headings.
    After each matching heading, insert the corresponding manual graph cards.
    Each section_key is injected at most once.
    """
    if not graphs_by_key:
        return body_html

    injected: set = set()

    for pattern, key in _MANUAL_SUB_PATTERNS:
        if key not in graphs_by_key or key in injected:
            continue
        entries = graphs_by_key[key]
        cards_html = _manual_graph_cards_html(entries, section_key=key)
        if not cards_html:
            continue

        # Try matching <h3> or <h4> containing the pattern
        def _replace_heading(m: re.Match) -> str:
            if key in injected:
                return m.group(0)
            tag_content = m.group(0)
            inner = re.sub(r"<[^>]+>", "", tag_content)  # strip tags for text match
            if pattern.search(inner):
                injected.add(key)
                return tag_content + "\n" + cards_html
            return tag_content

        new_html = re.sub(r"<h[34][^>]*>.*?</h[34]>", _replace_heading, body_html, flags=re.DOTALL)

        # If not matched via h3/h4, try <p><strong> patterns
        if key not in injected:
            def _replace_strong(m: re.Match) -> str:
                if key in injected:
                    return m.group(0)
                inner = re.sub(r"<[^>]+>", "", m.group(0))
                if pattern.search(inner):
                    injected.add(key)
                    return m.group(0) + "\n" + cards_html
                return m.group(0)
            new_html = re.sub(r"<p[^>]*><strong>.*?</strong></p>", _replace_strong, new_html, flags=re.DOTALL)

        body_html = new_html

    return body_html


# ── Main v2 public function ────────────────────────────────────────────────────

def generate_html_report_v2(
    output_dir: Path,
    processed_dir: Optional[Path] = None,
) -> Path:
    """
    Generate a Goldman-style institutional research dashboard (report_v2.html).

    Reads final_report.md from output_dir, optionally reads KPI counts from
    processed_dir (auto-detected if not passed).  Produces a self-contained
    single-file HTML with hero KPI cards, dark-navy sidebar, section thesis
    cards, risk grid, and chart-card containers.

    Preserves report.html (v1) — does not overwrite it.
    """
    output_dir = Path(output_dir)

    main_md_path = output_dir / "final_report.md"
    if not main_md_path.exists():
        raise FileNotFoundError(f"final_report.md not found in {output_dir}")

    main_md = main_md_path.read_text(encoding="utf-8")
    title, gen_date = _extract_title_and_date(main_md)
    sector_label = (
        title.replace("Investment Research Report:", "").replace("行业深度研究报告", "").strip()
    ) or title

    # ── KPI data ────────────────────────────────────────────────────────────────
    kpis = _extract_kpi_data(output_dir, processed_dir)

    # ── Industry charts ─────────────────────────────────────────────────────────
    try:
        from src.reporting.industry_chart_extractor import load_industry_charts
        industry_charts_by_section: Dict[str, List[dict]] = load_industry_charts(output_dir)
    except Exception as _exc:
        logger.warning("Could not load industry charts: %s", _exc)
        industry_charts_by_section = {}

    # ── Manual graphs (data/raw/graphs/) ─────────────────────────────────────────
    try:
        from src.reporting.manual_graph_inserter import load_manual_graphs
        manual_graphs_by_key = load_manual_graphs()
    except Exception as _exc:
        logger.warning("Could not load manual graphs: %s", _exc)
        manual_graphs_by_key = {}

    # ── Sourcing ranking charts ──────────────────────────────────────────────────
    sourcing_charts_html = _charts_block_v2(output_dir / "charts")

    # ── Parse sections ───────────────────────────────────────────────────────────
    raw_sections = _extract_sections(main_md)

    sections_data: List[dict] = []
    for idx, (heading, body_md) in enumerate(raw_sections):
        if not heading:
            continue
        anchor_id = _slugify(heading)
        body_html = _md_to_html(body_md)
        body_html = _add_h3_anchors(body_html)
        body_html = _stylize_citations(body_html)
        body_html = _conviction_badge(body_html)
        # Inject manual graphs after matching subsection headings
        body_html = _inject_manual_graphs_into_body(body_html, manual_graphs_by_key)

        is_risk = "风险" in heading
        is_validation = heading in ("Validation Notes", "数据质量说明", "七、数据质量说明")

        if is_validation:
            body_html = _wrap_validation_notes(body_html)

        thesis = _extract_section_thesis(body_md)
        risk_cards = _parse_risk_cards(body_md) if is_risk else []

        sections_data.append({
            "heading": heading,
            "anchor_id": anchor_id,
            "body_html": body_html,
            "body_md": body_md,
            "thesis": thesis,
            "risk_cards": risk_cards,
            "num": f"{idx + 1:02d}",
            "is_risk": is_risk,
        })

    # ── Sidebar TOC ─────────────────────────────────────────────────────────────
    toc_items = []
    for s in sections_data:
        toc_items.append(f'<a href="#{s["anchor_id"]}">{s["heading"]}</a>')
        for m in re.finditer(r'<h3 id="([^"]+)">([^<]+)</h3>', s["body_html"]):
            toc_items.append(f'<a class="h3" href="#{m.group(1)}">{m.group(2)}</a>')
    toc_html = "\n".join(toc_items)

    # ── Build section HTML ───────────────────────────────────────────────────────
    sourcing_inserted = False
    body_parts: List[str] = []

    for s in sections_data:
        heading    = s["heading"]
        anchor_id  = s["anchor_id"]
        body_html  = s["body_html"]
        thesis     = s["thesis"]
        risk_cards = s["risk_cards"]
        num        = s["num"]
        is_risk    = s["is_risk"]

        body_parts.append(f'<section class="report-section" id="{anchor_id}">')

        # Section header bar
        body_parts.append(
            f'<div class="section-header">'
            f'<span class="section-num">{num}</span>'
            f'<h2>{heading}</h2>'
            f"</div>"
        )

        body_parts.append('<div class="section-body-wrap">')

        # Thesis card
        if thesis:
            body_parts.append(
                f'<div class="thesis-card">'
                f'<div class="thesis-label">核心判断</div>'
                f'<div class="thesis-text">{thesis}</div>'
                f"</div>"
            )

        # Risk section: grid cards first, then full body for detail
        if is_risk and risk_cards:
            body_parts.append(_build_risk_cards_html(risk_cards))
        body_parts.append(body_html)

        # Sourcing ranking chart after sourcing section
        if not sourcing_inserted and sourcing_charts_html and heading in (
            "2.1 Sourcing：公司筛选与市场地图",
            "Private Market Overview",
            "二、一级市场分析",
        ):
            body_parts.append(sourcing_charts_html)
            sourcing_inserted = True

        # Per-section industry charts
        sec_charts = industry_charts_by_section.get(heading, [])
        if sec_charts:
            ic_html = _render_industry_charts_html_v2(sec_charts)
            if ic_html:
                body_parts.append(ic_html)

        body_parts.append("</div>")  # section-body-wrap
        body_parts.append("</section>")

    if not sourcing_inserted and sourcing_charts_html:
        body_parts.append(sourcing_charts_html)

    body_html_full = "\n".join(body_parts)

    # ── KPI cards ───────────────────────────────────────────────────────────────
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    kpi_cards_html = _build_kpi_cards_html(kpis, gen_date or now_str)

    # ── Assemble HTML ────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{_CSS_V2}</style>
</head>
<body>

<!-- ── Sidebar ──────────────────────────────────────── -->
<aside id="sidebar">
  <div class="sidebar-brand">AI 投研系统</div>
  <div class="sidebar-label">目录</div>
  <nav>
    {toc_html}
  </nav>
  <div class="sidebar-footer">AI Investing Research Pipeline</div>
</aside>

<!-- ── Main content ─────────────────────────────────── -->
<div id="content">

  <!-- Hero -->
  <div class="hero">
    <div class="hero-eyebrow">行业深度研究报告</div>
    <h1>{sector_label if sector_label else title}</h1>
    <div class="hero-meta">{gen_date or now_str}&nbsp;·&nbsp;AI投研系统&nbsp;·&nbsp;Powered by Claude</div>
    <div class="kpi-row">
      {kpi_cards_html}
    </div>
  </div>

  <!-- Disclaimer strip -->
  <div class="disclaimer">
    <strong>免责声明：</strong>本报告由AI研究流程自动生成，仅供学术研究与教学使用，不构成任何投资建议。所有数据须经独立核实后方可使用。
  </div>

  <!-- Report sections -->
  <div class="content-wrapper">
    {body_html_full}
  </div>

  <!-- Footer -->
  <div class="report-footer">
    <span>生成时间：{now_str}&nbsp;·&nbsp;AI Investing Research Pipeline</span>
    <span>仅供学术使用，不构成投资建议</span>
  </div>

</div>

<script>{_JS_V2}</script>
</body>
</html>"""

    out_path = output_dir / "report_v2.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("[html_report_v2] Saved → %s  (%d KB)", out_path.name, len(html) // 1024)
    return out_path
