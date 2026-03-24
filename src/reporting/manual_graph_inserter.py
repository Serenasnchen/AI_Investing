"""
ManualGraphInserter: maps files from data/raw/graphs/ to report sections.

Matching rules (filename keyword → section anchor):
  "AI在制药中的角色" | "ai在制药中的角色"  → section_key "role"
  "市场规模与增速"                          → section_key "market_size"
  "公司筛选与市场地图"                      → section_key "sourcing_map"
  "竞争格局"                               → section_key "competition"
  "商业模式"                               → section_key "biz_model"

Returns a dict[section_key → List[GraphEntry]] sorted by filename.
"""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

GRAPHS_DIR = Path(__file__).parents[2] / "data" / "raw" / "graphs"

# (keyword_pattern, section_key, human_label)
_RULES: list = [
    (re.compile(r"AI在制药中的角色|ai在制药中的角色", re.IGNORECASE), "role",         "AI在制药中的角色"),
    (re.compile(r"市场规模与增速"),                                   "market_size",  "市场规模与增速"),
    (re.compile(r"公司筛选与市场地图"),                                "sourcing_map", "公司筛选与市场地图"),
    (re.compile(r"竞争格局"),                                         "competition",  "竞争格局"),
    (re.compile(r"商业模式"),                                         "biz_model",    "商业模式分类"),
]


@dataclass
class GraphEntry:
    path: Path
    section_key: str
    label: str          # human-readable section label
    caption: str        # short caption shown under the image


def load_manual_graphs(graphs_dir: Optional[Path] = None) -> Dict[str, List[GraphEntry]]:
    """
    Scan graphs_dir for PNG/JPG files, match each against _RULES,
    return {section_key: [GraphEntry, ...]} sorted by filename.
    Unmatched files are logged as warnings.
    """
    root = graphs_dir or GRAPHS_DIR
    result: Dict[str, List[GraphEntry]] = {}

    if not root.exists():
        logger.warning("[ManualGraphs] graphs_dir does not exist: %s", root)
        return result

    files = sorted(p for p in root.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not files:
        logger.warning("[ManualGraphs] No image files found in %s", root)
        return result

    for f in files:
        matched = False
        for pattern, key, label in _RULES:
            if pattern.search(f.name):
                entry = GraphEntry(
                    path=f,
                    section_key=key,
                    label=label,
                    caption=f.stem,   # use filename stem as default caption
                )
                result.setdefault(key, []).append(entry)
                logger.info("[ManualGraphs] %s → section '%s'", f.name, key)
                matched = True
                break
        if not matched:
            logger.warning("[ManualGraphs] No matching section for file: %s", f.name)

    return result
