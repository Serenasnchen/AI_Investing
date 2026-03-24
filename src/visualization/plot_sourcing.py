"""
plot_sourcing: bar chart of SourcingAgent screening scores.

Reads sourcing_screening_results.json from the run's processed directory
and saves outputs/{run_id}/charts/sourcing_ranking.png.
"""
import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


def plot_sourcing_ranking(
    screening_results_path: Path,
    output_dir: Path,
) -> Path:
    """
    Draw a horizontal bar chart of company total_scores from
    sourcing_screening_results.json.

    Args:
        screening_results_path: Path to sourcing_screening_results.json.
        output_dir: Run-level output directory (outputs/{run_id}/).

    Returns:
        Path to the saved PNG file.
    """
    import matplotlib
    matplotlib.use("Agg")   # non-interactive backend — safe on headless servers
    import matplotlib.pyplot as plt

    # ── Load data ─────────────────────────────────────────────────────────
    with screening_results_path.open(encoding="utf-8") as f:
        records = json.load(f)

    names: List[str] = [r["startup"]["name"] for r in records]
    scores: List[float] = [r["total_score"] for r in records]

    # Sort descending so highest score is at the top of a horizontal bar chart
    paired = sorted(zip(scores, names), reverse=True)
    scores_sorted = [s for s, _ in paired]
    names_sorted  = [n for _, n in paired]

    # ── Draw chart ────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, max(4, len(names_sorted) * 0.7)))

    y_pos = range(len(names_sorted))
    ax.barh(list(y_pos), scores_sorted)

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(names_sorted)
    ax.invert_yaxis()          # highest score at the top

    ax.set_xlabel("Total Score (out of 25)")
    ax.set_title("SourcingAgent — Company Screening Rankings")
    ax.set_xlim(0, 25)

    # Annotate each bar with the numeric score
    for i, score in enumerate(scores_sorted):
        ax.text(score + 0.2, i, f"{score:.1f}", va="center", fontsize=9)

    plt.tight_layout()

    # ── Save ──────────────────────────────────────────────────────────────
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    out_path = charts_dir / "sourcing_ranking.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    logger.info("[plot_sourcing] Saved chart → %s", out_path)
    return out_path
