# CLAUDE.md — AI Investing Research Workflow

## Project Purpose
Agentic investment research pipeline for an "AI-driven Primary & Secondary Investment Research Workflow" course project. Generates institutional-quality research reports for any sector using 5 specialized Claude-powered agents.

## Key Commands
```bash
python main.py --sector "AI drug discovery"          # Run full pipeline
python main.py --sector "climate tech" -v            # Run with debug logging
pip install -r requirements.txt                      # Install dependencies
```

## Architecture Overview
- **5 agents** in `src/agents/`: sourcing → diligence → public_market → validator → report_writer
- **Orchestrator** in `src/pipelines/orchestrator.py` sequences the agents
- **Pydantic models** in `src/models/` for all inter-agent data transfer
- **Prompt templates** in `prompts/*.md` — injected with `{sector}` at runtime
- **Config** in `src/config.py` — all settings via `.env` / `SectorConfig` dataclass

## Adding a New Sector
1. Pass `--sector "your sector"` on the CLI — no code changes needed
2. Optionally pass `--tickers` to hint the public market agent

## Adding a New Agent
1. Create `src/agents/your_agent.py` extending `BaseAgent`
2. Add a prompt template to `prompts/your_agent.md`
3. Register in `src/agents/__init__.py`
4. Add to the orchestrator sequence in `src/pipelines/orchestrator.py`

## Data Flow
```
CLI → SectorConfig → Orchestrator → Agents → Pydantic models → JSON in data/processed/ → Final .md in outputs/
```

## Never
- Hardcode API keys anywhere in source
- Commit `.env` (only `.env.example` is tracked)
