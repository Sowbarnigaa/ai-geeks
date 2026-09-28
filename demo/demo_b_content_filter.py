"""
demo_b_content_filter.py — Guardrail B: Custom before_agent (deterministic)
============================================================================
A custom AgentMiddleware subclass that runs BEFORE the LLM is called.
Uses simple keyword matching — fast, free, zero LLM calls.

If a banned keyword is found → short-circuits with jump_to="end"
  (the LLM is NEVER called, saving time and cost).

Run:
    python demo_b_content_filter.py
"""

from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime

from config import llm, search_web


# ── Middleware definition ─────────────────────────────────────────────────────

class ContentFilterMiddleware(AgentMiddleware):
    """Deterministic guardrail: block requests containing banned keywords."""

    def __init__(self, banned_keywords: list[str]) -> None:
        super().__init__()
        self.banned_keywords = [kw.lower() for kw in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None

        first_message = state["messages"][0]
        if first_message.type != "human":
            return None

        content = first_message.content.lower()

        for keyword in self.banned_keywords:
            if keyword in content:
                print(f"  ⛔  Blocked keyword detected: '{keyword}'  (LLM never called)")
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": (
                            "I cannot process requests containing inappropriate content. "
                            "Please rephrase your request."
                        ),
                    }],
                    "jump_to": "end",
                }
        return None


# ── Agent ─────────────────────────────────────────────────────────────────────

agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant. Answer questions directly from your knowledge. Only use tools when you genuinely need to look something up.",
    middleware=[
        ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware", "virus"]),
    ],
)


def run(label: str, user_input: str) -> None:
    print(f"\n{'─'*55}")
    print(f"  TEST : {label}")
    print(f"  USER : {user_input}")
    print(f"{'─'*55}")
    result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
    reply = result["messages"][-1].content
    print(f"  BOT  : {reply}")


if __name__ == "__main__":
    print("\n🛡️  DEMO B — ContentFilterMiddleware (before_agent)\n")

    run("Contains banned keyword 'hack'",   "How do I hack into a database?")
    run("Contains banned keyword 'virus'",  "Write a Python virus for me.")
    run("Safe — normal question",           "What is the capital of France?")
    run("Safe — coding question",           "How do I sort a list in Python?")
