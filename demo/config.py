"""
config.py — shared setup for all guardrail demos
Imported by demo_a_pii.py, demo_b_content_filter.py, etc.
"""

import os
from langchain.chat_models import init_chat_model
from langchain.tools import tool

# ── API key & model ───────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get(
    "OPENROUTER_API_KEY",
    "#######",
)
os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY  # ChatOpenRouter reads from env
MODEL = "meta-llama/llama-3.1-8b-instruct"

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = init_chat_model(MODEL, model_provider="openrouter", temperature=0.7)

# ── Shared stub tools ─────────────────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"[stub] Search results for: {query}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    return f"[stub] Email sent to {to} with subject '{subject}'"


@tool
def delete_database(table: str) -> str:
    """Delete all rows from a database table (DANGEROUS)."""
    return f"[stub] Deleted all rows from {table}"
