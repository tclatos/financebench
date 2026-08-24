"""Shared environment and path constants for the financebench bench harness.

Loads ``~/.env`` so API keys (``HF_TOKEN``, ``MISTRAL_API_KEY``,
``OPENROUTER_API_KEY`` ...) are available when the bench scripts run via
``uv run python -m financebench.bench.<module>`` rather than the ``cli``
entry point (which loads dotenv itself).

All paths are derived from this file's location so the scripts work from any
current working directory.
"""

from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
PDFS_DIR = DATA_DIR / "pdfs"
MARKDOWN_DIR = DATA_DIR / "markdown"
KG_DB = DATA_DIR / "kg" / "financebench_tree.db"
FB_DIR = DATA_DIR / "financebench"
REPORT_DIR = PROJECT_ROOT / "report"

ONEDRIVE = Path.home() / "OneDrive"
ONEDRIVE_MARKDOWN_DIR = ONEDRIVE / "prj" / "financebench" / "markdown"

DEFAULT_AGENT_LLM = "deepseek_v4flash@openrouter"
DEFAULT_JUDGE_LLM = "deepseek_v4flash@openrouter"
# Flash LLM used by the LLM-enhanced Document Graph build (--llm) to discover
# each document's outline (TOC + descriptions + section summaries) in one call.
DEFAULT_BUILD_LLM = "deepseek_v4flash@openrouter"


def load_env() -> None:
    """Load ``~/.env`` (idempotent) so secrets are present in ``os.environ``."""
    home_env = Path.home() / ".env"
    if home_env.exists():
        load_dotenv(home_env, override=False)


def ensure_dirs() -> None:
    """Create the bench working directories if they do not yet exist."""
    for d in (PDFS_DIR, MARKDOWN_DIR, KG_DB.parent, FB_DIR, REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)
