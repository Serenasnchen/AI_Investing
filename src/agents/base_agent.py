"""
Abstract base class for all research agents.
"""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

import anthropic

from src.config import SectorConfig, PROMPTS_DIR
from .mock_responses import MOCK_RESPONSES

logger = logging.getLogger(__name__)

# Domains that indicate a placeholder / invented URL.
_PLACEHOLDER_DOMAINS = (
    "example.com",
    "example.org",
    "placeholder.com",
    "test.com",
    "yourdomain.com",
    "domain.com",
)


def _repair_truncated_json(text: str) -> Optional[Any]:
    """
    Attempt to recover a valid JSON value from a truncated string.

    Strategy: walk backwards from the end of the string looking for the
    last position where the bracket/brace depth returns to zero, then try
    parsing the substring up to that point.

    Returns the parsed object if successful, None if no valid prefix found.
    """
    if not text:
        return None

    # Determine the outermost container character
    first = text[0]
    if first == "{":
        open_ch, close_ch = "{", "}"
    elif first == "[":
        open_ch, close_ch = "[", "]"
    else:
        return None

    # Find the last position where depth reaches 0
    depth = 0
    last_close = -1
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                last_close = i

    if last_close == -1:
        return None

    candidate = text[: last_close + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def is_placeholder_url(url: str) -> bool:
    """Return True if the URL uses a known placeholder/fake domain."""
    if not url:
        return False
    url_lower = url.lower()
    return any(domain in url_lower for domain in _PLACEHOLDER_DOMAINS)


class BaseAgent(ABC):
    """
    Base class that handles:
    - Loading prompt templates from prompts/
    - Calling Claude API via Anthropic SDK
    - Basic error logging
    """

    prompt_file: str  # subclasses must set this, e.g. "sourcing.md"

    def __init__(self, config: SectorConfig):
        self.config = config
        # Skip real client initialisation in mock mode (no API key needed)
        self.client = (
            None if config.use_mock_llm
            else anthropic.Anthropic(api_key=config.anthropic_api_key)
        )
        self._prompt_template: Optional[str] = None

    def _load_prompt(self) -> str:
        if self._prompt_template is None:
            path = PROMPTS_DIR / self.prompt_file
            if not path.exists():
                raise FileNotFoundError(f"Prompt file not found: {path}")
            self._prompt_template = path.read_text(encoding="utf-8")
        return self._prompt_template

    def _render_prompt(self, **kwargs) -> str:
        """Inject variables (including sector) into the prompt template."""
        template = self._load_prompt()
        return template.format(sector=self.config.sector, **kwargs)

    def _call_llm(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Claude and return the text response.

        In mock mode (USE_MOCK_LLM=true) the API is never contacted; a
        pre-written response is returned immediately instead.
        """
        agent_name = self.__class__.__name__

        if self.config.use_mock_llm:
            mock_text = MOCK_RESPONSES.get(agent_name)
            if mock_text is None:
                raise NotImplementedError(
                    f"No mock response defined for {agent_name}. "
                    "Add an entry to src/agents/mock_responses.py."
                )
            logger.info("[%s] MOCK MODE — skipping API call, returning mock response.", agent_name)
            return mock_text

        # --- real API path ---
        messages = [{"role": "user", "content": user_prompt}]
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        logger.info("[%s] Calling %s ...", agent_name, self.config.model)
        response = self.client.messages.create(**kwargs)
        text = response.content[0].text
        stop_reason = getattr(response, "stop_reason", None)
        logger.info(
            "[%s] Received %d chars (stop_reason=%s).",
            agent_name, len(text), stop_reason,
        )
        if stop_reason == "max_tokens":
            logger.warning(
                "[%s] Response hit max_tokens limit (%d). "
                "Output may be truncated — set MAX_TOKENS env var to increase.",
                agent_name, self.config.max_tokens,
            )
        return text

    def _parse_json(self, text: str) -> Any:
        """
        Extract JSON from a response that may contain Markdown fences.

        If standard parsing fails (e.g. truncated output), attempts a best-effort
        repair by finding the last complete top-level object/array bracket.
        """
        # Strip ```json ... ``` or ``` ... ``` fences if present
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            stripped = "\n".join(lines[1:-1]).strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            # Best-effort repair: try truncating to the last balanced bracket
            repaired = _repair_truncated_json(stripped)
            if repaired is not None:
                logger.warning(
                    "JSON was malformed (pos %d) — recovered via truncation repair. "
                    "Consider raising MAX_TOKENS if this recurs.",
                    exc.pos,
                )
                return repaired
            raise

    @abstractmethod
    def run(self, *args, **kwargs):
        """Execute the agent. Subclasses define inputs and return typed models."""
        ...
