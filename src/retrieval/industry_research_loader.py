"""
IndustryResearchLoader: 读取 data/industryresearch/ 下的 PDF 并切分为可检索的 chunks。

每个 chunk 保留：
  text         — chunk 文本（120–1200 字符）
  source_file  — PDF 文件名（用作引用键，如 "中邮证券_2026-01-22.pdf"）
  source_label — 可读引用标签（如 "中邮证券 2026-01-22"）
  source_type  — 固定为 "sell_side_report"
  reliability  — 固定为 "high"
  chunk_index  — 文档内顺序编号
  page_number  — PDF 页码（1-based）

切分策略：
  1. 按页提取文本（pypdf）
  2. 每页先按双换行分割段落
  3. 超长段落按句号/问号/叹号边界二次切分
  4. 合并过短 fragment 至 MIN_CHARS
  5. 丢弃明显噪声（页眉页脚、纯数字行）

用法：
    from src.retrieval.industry_research_loader import load_industry_reports
    chunks = load_industry_reports()           # 从默认 data/industryresearch/
    chunks = load_industry_reports(my_dir)     # 自定义目录
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── 切分参数 ──────────────────────────────────────────────────────────────────
MIN_CHARS = 120
MAX_CHARS = 1_200
OVERLAP   = 80


# ── 数据结构 ──────────────────────────────────────────────────────────────────

@dataclass
class IndustryReportChunk:
    """来自券商/行业研报 PDF 的单个文本 chunk。"""
    text: str
    source_file: str          # 原始文件名，如 "中邮证券_2026-01-22.pdf"
    source_label: str         # 引用标签，如 "中邮证券 2026-01-22"
    source_type: str = "sell_side_report"
    reliability: str = "high"
    chunk_index: int = 0
    page_number: Optional[int] = None


# ── 文件名解析 ─────────────────────────────────────────────────────────────────

def parse_source_label(filename: str) -> str:
    """
    从 PDF 文件名解析出可读的引用标签。

    支持的命名规范（按优先级）：

    1. 日期前缀格式（最常见，如中国券商研报命名）：
       2026-01-22_中邮证券_医药生物_AI制药...pdf  → "中邮证券 2026-01-22"
       2025-12-11_国金证券_医药生物_...pdf         → "国金证券 2025-12-11"

    2. 日期后缀格式：
       中邮证券_2026-01-22.pdf                    → "中邮证券 2026-01-22"
       GoldmanSachs_2025-09.pdf                   → "GoldmanSachs 2025-09"

    3. 兜底：使用完整文件名（截断至40字符）
    """
    stem = Path(filename).stem
    parts = stem.split("_")

    # Pattern 1: date-prefixed — first segment is YYYY-MM-DD or YYYYMMDD
    if parts and re.match(r"^\d{4}[-]\d{2}[-]\d{2}$|^\d{8}$", parts[0]):
        date = parts[0]
        broker = parts[1] if len(parts) > 1 else stem
        return f"{broker} {date}"

    # Pattern 2: date-suffixed — last segment is a date
    if len(parts) >= 2:
        prefix, suffix = "_".join(parts[:-1]), parts[-1]
        if re.match(r"^\d{4}[-.]?\d{0,2}[-.]?\d{0,2}$", suffix):
            return f"{prefix} {suffix}"

    # Fallback: truncate long stems
    return stem[:40] if len(stem) > 40 else stem


# ── PDF 加载 ──────────────────────────────────────────────────────────────────

def load_industry_reports(directory: Optional[Path] = None) -> List[IndustryReportChunk]:
    """
    从指定目录读取所有 PDF，返回 IndustryReportChunk 列表。

    Args:
        directory: 研报 PDF 所在目录（默认 data/industryresearch/）。

    Returns:
        按 (source_file, chunk_index) 排序的 chunk 列表。
        如果目录不存在或没有 PDF，返回空列表（不抛出异常）。
    """
    if directory is None:
        from src.config import DATA_RAW_DIR
        # data/raw/ 的父目录下的 industryresearch/
        directory = DATA_RAW_DIR.parent / "industryresearch"

    if not directory.exists():
        logger.warning("[IndustryLoader] 目录不存在: %s — 自动创建中。", directory)
        directory.mkdir(parents=True, exist_ok=True)
        return []

    pdf_files = sorted(directory.glob("*.pdf"))
    if not pdf_files:
        logger.info("[IndustryLoader] %s 中没有 PDF 文件。", directory)
        return []

    all_chunks: List[IndustryReportChunk] = []
    for pdf_path in pdf_files:
        try:
            chunks = _load_one_pdf(pdf_path)
            all_chunks.extend(chunks)
            logger.info("[IndustryLoader] %s → %d chunks", pdf_path.name, len(chunks))
        except Exception as exc:
            logger.warning("[IndustryLoader] 加载失败 %s: %s", pdf_path.name, exc)

    logger.info(
        "[IndustryLoader] 共加载 %d chunks，来自 %d 个 PDF。",
        len(all_chunks), len(pdf_files),
    )
    return all_chunks


# ── 内部辅助函数 ───────────────────────────────────────────────────────────────

def _load_one_pdf(pdf_path: Path) -> List[IndustryReportChunk]:
    """读取并切分单个 PDF 文件。"""
    import pypdf

    source_file  = pdf_path.name
    source_label = parse_source_label(source_file)

    reader = pypdf.PdfReader(str(pdf_path))
    raw_fragments: List[Tuple[int, str]] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        for frag in _split_page(text):
            raw_fragments.append((page_num, frag))

    return _merge_fragments(raw_fragments, source_file, source_label)


def _split_page(text: str) -> List[str]:
    """将单页文本分割为候选 fragment 列表。"""
    text = re.sub(r" {2,}", " ", text)
    parts = re.split(r"\n{2,}", text)
    fragments = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= MAX_CHARS:
            fragments.append(part)
        else:
            # 超长段落按句子边界二次切分（中英文标点）
            sentences = re.split(r"(?<=[。！？.!?])\s*", part)
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
    raw_fragments: List[Tuple[int, str]],
    source_file: str,
    source_label: str,
) -> List[IndustryReportChunk]:
    """合并短 fragment，生成带重叠的最终 chunks。"""
    chunks = []
    chunk_index = 0
    buffer_text = ""
    buffer_page = None

    for page_num, frag in raw_fragments:
        cleaned = frag.strip()
        if len(cleaned) < 30:
            continue
        if _is_noise(cleaned):
            continue

        if buffer_page is None:
            buffer_page = page_num

        buffer_text = (buffer_text + "\n" + cleaned).strip() if buffer_text else cleaned

        if len(buffer_text) >= MIN_CHARS:
            chunks.append(IndustryReportChunk(
                text=buffer_text[:MAX_CHARS],
                source_file=source_file,
                source_label=source_label,
                chunk_index=chunk_index,
                page_number=buffer_page,
            ))
            chunk_index += 1
            buffer_text = buffer_text[-OVERLAP:] if len(buffer_text) > OVERLAP else ""
            buffer_page = page_num

    if buffer_text and len(buffer_text) >= MIN_CHARS // 2:
        chunks.append(IndustryReportChunk(
            text=buffer_text[:MAX_CHARS],
            source_file=source_file,
            source_label=source_label,
            chunk_index=chunk_index,
            page_number=buffer_page,
        ))
    return chunks


_NOISE_RE = re.compile(
    r"^(\d+|[ivxlcdm]+|page \d+|第\s*\d+\s*[页页]|©.*|版权.*|all rights reserved.*"
    r"|doi:.*|https?://\S+)$",
    re.IGNORECASE,
)


def _is_noise(text: str) -> bool:
    """过滤纯元数据行（页眉、页脚、页码等）。"""
    stripped = text.strip()
    if _NOISE_RE.match(stripped):
        return True
    words = stripped.split()
    # 少于 3 个词且无标点 → 可能是标题或页眉
    if len(words) <= 2 and not any(c in stripped for c in "。.,:;，："):
        return True
    return False
