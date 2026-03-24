"""
IndustryResearchRetriever: 面向券商/行业研报的双语关键词检索引擎。

从 IndustryResearchLoader 加载的 chunks 构建内存倒排索引，
支持中英文混合查询。

证据优先级：industry_report > paper/pubmed > web > inference

公开接口
--------
    retriever = IndustryResearchRetriever()
    results   = retriever.search_industry_reports("AI制药 市场规模 增长", top_k=5)
    block     = retriever.format_for_llm(results)

引用格式（写入 prompt）：[来源：中邮证券 2026-01-22，第3页]
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from .industry_research_loader import IndustryReportChunk, load_industry_reports

logger = logging.getLogger(__name__)


# ── 检索结果 ──────────────────────────────────────────────────────────────────

@dataclass
class IndustryReportSearchResult:
    """IndustryResearchRetriever.search_industry_reports() 返回的单条结果。"""
    chunk_text: str
    source_file: str
    source_label: str         # 用于 [来源：...] 格式
    source_type: str = "sell_side_report"
    reliability: str = "high"
    score: float = 0.0
    chunk_index: int = 0
    page_number: Optional[int] = None


# ── 双语 tokeniser ─────────────────────────────────────────────────────────────

_STOP_WORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "this", "that", "these", "those", "it", "its",
    "as", "which", "who", "what", "how", "when", "where", "not", "also",
    "than", "more", "such", "their", "they", "we", "our", "can",
}


def _tokenise(text: str) -> Set[str]:
    """
    双语 tokeniser：同时提取英文词和中文字符。

    英文：小写化，≥3 字符，去停用词。
    中文：单个汉字（支持部分词匹配）。
    """
    tokens: Set[str] = set()
    for t in re.findall(r"[a-z]{3,}", text.lower()):
        if t not in _STOP_WORDS:
            tokens.add(t)
    for ch in re.findall(r"[\u4e00-\u9fff]", text):
        tokens.add(ch)
    return tokens


# ── IndustryResearchRetriever ──────────────────────────────────────────────────

class IndustryResearchRetriever:
    """
    在构建时从研报目录加载所有 PDF chunks，建立双语倒排索引。

    Args:
        directory: 覆盖默认的 data/industryresearch/ 目录。
    """

    # 5 类必查 query（ReportWriterAgent 默认使用）
    DEFAULT_QUERIES = [
        "AI制药 市场规模 增长 驱动因素",
        "AI制药 商业模式 数据壁垒",
        "AI制药 竞争格局 龙头 公司",
        "AI制药 应用阶段 临床前 降本增效",
        "AI制药 风险提示",
    ]

    def __init__(self, directory: Optional[Path] = None):
        self._chunks: List[IndustryReportChunk] = load_industry_reports(directory)
        self._index: Dict[str, List[int]] = {}
        self._token_sets: List[Set[str]] = []
        self._build_index()

    # ── 公开 API ───────────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return len(self._chunks) == 0

    def search_industry_reports(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[IndustryReportSearchResult]:
        """
        对给定 query（中/英文均可）返回 top_k 个最相关 chunks。

        Args:
            query:  自然语言查询字符串。
            top_k:  最多返回条数。

        Returns:
            按相关度降序排列的 IndustryReportSearchResult 列表。
        """
        if self.is_empty:
            return []

        query_terms = _tokenise(query)
        if not query_terms:
            return []

        # 候选 chunk：取所有命中 token 的 posting list 并集
        candidate_indices: Set[int] = set()
        for term in query_terms:
            candidate_indices.update(self._index.get(term, []))

        # 4 字前缀回退（处理词根变形）
        if not candidate_indices:
            prefixes = {t[:4] for t in query_terms if len(t) >= 4}
            for term, posting in self._index.items():
                if any(term.startswith(p) for p in prefixes):
                    candidate_indices.update(posting)

        if not candidate_indices:
            return []

        scored = [
            (self._score(idx, query_terms), idx)
            for idx in candidate_indices
        ]
        scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(key=lambda x: -x[0])

        results = []
        for score, idx in scored[:top_k]:
            c = self._chunks[idx]
            results.append(IndustryReportSearchResult(
                chunk_text=c.text,
                source_file=c.source_file,
                source_label=c.source_label,
                score=round(score, 4),
                chunk_index=c.chunk_index,
                page_number=c.page_number,
            ))
        return results

    def format_for_llm(
        self,
        results: List[IndustryReportSearchResult],
        label: str = "行业研报证据（最高优先级）",
        max_chars_per_chunk: int = 800,
    ) -> str:
        """
        将检索结果渲染为 LLM prompt 注入格式。

        每条结果格式：
            [来源：中邮证券 2026-01-22，第3页]
            <chunk 文本>

        如果 results 为空，返回要求使用弱化语气的指令。
        """
        if not results:
            return (
                f"## {label}\n\n"
                "**【无研报支持】** data/industryresearch/ 目录下暂无行业研报。\n"
                "对所有行业判断（市场规模、竞争格局、商业模式、增长驱动），"
                "必须使用弱化语气（如：据公开信息、市场普遍认为），"
                "严禁给出无来源的强结论。"
            )

        lines = [f"## {label}\n"]
        seen_labels: Set[str] = set()
        for i, r in enumerate(results, 1):
            page_str = f"，第{r.page_number}页" if r.page_number else ""
            citation = f"[来源：{r.source_label}{page_str}]"
            lines.append(f"**[{i}]** {citation}")
            text = r.chunk_text
            if len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk] + "……"
            lines.append(text)
            lines.append("")
            seen_labels.add(r.source_label)

        example_label = next(iter(seen_labels))
        lines.append(
            "---\n"
            "**【强制引用规则】**\n"
            f"- 引用上述研报内容时，必须使用格式：`[来源：机构名 日期，第X页]`，"
            f"例如 `[来源：{example_label}，第1页]`。\n"
            "- 研报已支持的结论 → **可以**使用强语气（数据显示、研报指出、我们判断）。\n"
            "- 研报未覆盖的行业结论 → **必须**弱化语气（据公开信息、市场估计）。\n"
            "- 严禁将研报内容归因于错误机构名，或虚构研报数据。"
        )
        return "\n".join(lines)

    def search_and_format(
        self,
        query: str,
        top_k: int = 5,
        label: Optional[str] = None,
    ) -> str:
        """便捷接口：检索后直接格式化输出。"""
        results = self.search_industry_reports(query, top_k=top_k)
        return self.format_for_llm(results, label=label or f'研报检索："{query}"')

    # ── 索引构建 ───────────────────────────────────────────────────────────────

    def _build_index(self) -> None:
        if not self._chunks:
            logger.info("[IndustryRetriever] 无 chunks 可索引。")
            return

        for idx, chunk in enumerate(self._chunks):
            tokens = _tokenise(chunk.text)
            self._token_sets.append(tokens)
            for token in tokens:
                self._index.setdefault(token, []).append(idx)

        logger.info(
            "[IndustryRetriever] 索引构建完成：%d chunks，%d 个唯一 token。",
            len(self._chunks), len(self._index),
        )

    def _score(self, chunk_idx: int, query_terms: Set[str]) -> float:
        """TF-overlap 得分，≥50% 覆盖率给 1.5× 奖励。"""
        matched = query_terms & self._token_sets[chunk_idx]
        if not matched:
            return 0.0
        base = len(matched) / max(len(query_terms), 1)
        return base * (1.5 if base >= 0.5 else 1.0)
