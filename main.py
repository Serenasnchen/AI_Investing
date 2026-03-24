"""
AI Investing Research Workflow
CLI entry point.

Usage:
    python main.py --sector "AI drug discovery"
    python main.py --sector "AI drug discovery" --diligence-count 2
    python main.py --sector "climate tech" --tickers ENPH FSLR RUN
"""
import argparse
import logging
import sys

from src.config import SectorConfig
from src.pipelines import ResearchOrchestrator


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-driven investment research workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --sector "AI drug discovery"
  python main.py --sector "climate tech" --tickers ENPH FSLR RUN
  python main.py --sector "autonomous vehicles" --diligence-count 2 --sourcing-count 6
        """,
    )
    parser.add_argument(
        "--sector",
        type=str,
        default="AI drug discovery",
        help='Research sector (default: "AI drug discovery")',
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Override example public tickers for this sector",
    )
    parser.add_argument(
        "--sourcing-count",
        type=int,
        default=8,
        help="Number of private companies to surface in sourcing (default: 8)",
    )
    parser.add_argument(
        "--diligence-count",
        type=int,
        default=3,
        help="Number of companies to deep-dive in diligence (default: 3)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    config = SectorConfig(sector=args.sector)
    if args.tickers:
        config.example_tickers = args.tickers
    if args.sourcing_count:
        config.sourcing_target_count = args.sourcing_count
    if args.diligence_count:
        config.diligence_target_count = args.diligence_count

    if config.use_mock_llm:
        print("\n" + "=" * 60)
        print("  MOCK MODE  (USE_MOCK_LLM=true)")
        print("  No API key required — using pre-written mock data.")
        print("=" * 60)

    try:
        orchestrator = ResearchOrchestrator(config)
        report = orchestrator.run()
        print("\n" + "=" * 60)
        print(f"  Report generated for: {report.sector}")
        if config.use_mock_llm:
            print("  [MOCK] Content is illustrative, not real research.")
        print("  Check the outputs/ directory for the full report.")
        print("=" * 60 + "\n")
    except EnvironmentError as e:
        print(f"\nConfiguration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).exception("Pipeline failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
