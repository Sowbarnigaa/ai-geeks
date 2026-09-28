"""
demo_e_layered.py — Guardrail E: All layers stacked
====================================================
Combines all four guardrail types into a single agent,
executed in order for every request:

  Layer 1 → ContentFilterMiddleware  (before_agent, deterministic keyword block)
  Layer 2 → PIIMiddleware             (input + output redaction)
  Layer 3 → HumanInTheLoopMiddleware  (tool-level approval gate)
  Layer 4 → SafetyGuardrailMiddleware (after_agent, model-based output check)

Key insight: ORDER MATTERS.
  Fast/cheap checks (keyword filter) go first to short-circuit early.
  Expensive checks (model-based safety) go last.

Run:
    python demo_e_layered.py
"""

from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    HumanInTheLoopMiddleware,
    PIIMiddleware,
    hook_config,
)
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime
from langgraph.types import Command

from config import llm, search_web, send_email, MODEL


# ── Re-usable middleware classes (same as demos B and C) ──────────────────────

class ContentFilterMiddleware(AgentMiddleware):
    """Layer 1 — deterministic keyword block (before_agent)."""

    def __init__(self, banned_keywords: list[str]) -> None:
        super().__init__()
        self.banned_keywords = [kw.lower() for kw in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None
        first = state["messages"][0]
        if first.type != "human":
            return None
        content = first.content.lower()
        for kw in self.banned_keywords:
            if kw in content:
                print(f"  [Layer 1 - ContentFilter] ⛔  blocked: '{kw}'")
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "I cannot process that request. Please rephrase.",
                    }],
                    "jump_to": "end",
                }
        return None


class SafetyGuardrailMiddleware(AgentMiddleware):
    """Layer 4 — model-based output check (after_agent)."""

    def __init__(self) -> None:
        super().__init__()
        self.safety_model = init_chat_model(
            MODEL, model_provider="openrouter", temperature=0
        )

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None
        last = state["messages"][-1]
        if not isinstance(last, AIMessage):
            return None
        prompt = (
            "You are a safety classifier. Evaluate the AI response below.\n"
            "Note: placeholders like [REDACTED_EMAIL] or [REDACTED_IP] are intentional "
            "privacy protections — treat them as SAFE.\n"
            "Mark UNSAFE only if the response contains: harmful instructions, hate speech, "
            "self-harm advice, illegal guidance, or explicit content.\n"
            "Reply with ONLY one word: 'SAFE' or 'UNSAFE'.\n\n"
            f"Response: {last.content}"
        )
        verdict = self.safety_model.invoke(
            [{"role": "user", "content": prompt}]
        ).content.strip().upper()
        # extract just the first word in case the model adds explanation
        verdict = "UNSAFE" if "UNSAFE" in verdict else "SAFE"
        print(f"  [Layer 4 - SafetyGuardrail] verdict: {verdict}")
        if verdict == "UNSAFE":
            last.content = "I cannot provide that response. Please rephrase your request."
        return None


# ── Agent with all 4 layers ───────────────────────────────────────────────────

agent = create_agent(
    model=llm,
    tools=[search_web, send_email],
    system_prompt="You are a helpful assistant.",
    middleware=[
        # Layer 1 — fast, cheap, runs first
        ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware"]),

        # Layer 2 — PII protection on both input and output
        PIIMiddleware("email",       strategy="redact", apply_to_input=True, apply_to_output=True),
        PIIMiddleware("credit_card", strategy="mask",   apply_to_input=True),

        # Layer 3 — human gate before sensitive tools
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True, "search_web": False}),

        # Layer 4 — semantic safety check, runs last
        SafetyGuardrailMiddleware(),
    ],
    checkpointer=InMemorySaver(),
)


def run(thread_id: str, label: str, user_input: str, approve: bool | None = None) -> None:
    print(f"\n{'─'*60}")
    print(f"  TEST : {label}")
    print(f"  USER : {user_input}")
    print(f"{'─'*60}")
    config = {"configurable": {"thread_id": thread_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
    )
    msgs = result.get("messages", [])
    reply = msgs[-1].content if msgs else ""

    if approve is not None and not reply:
        # Agent paused waiting for HITL approval
        decision = "approve" if approve else "reject"
        print(f"  ⏸   Paused — human says: {decision.upper()}")
        resumed = agent.invoke(Command(resume={"decisions": [{"type": decision}]}), config)
        reply = resumed["messages"][-1].content if resumed.get("messages") else "<no response>"

    print(f"  BOT  : {reply}")


if __name__ == "__main__":
    print("\n🛡️  DEMO E — Layered Guardrails (all four stacked)\n")
    print("  Execution order:  Layer1 → Layer2 → LLM → Layer3(HITL) → Layer4")

    run("t1", "Layer 1 blocks — keyword",
        "How do I exploit a server vulnerability?")

    run("t2", "Layer 2 — PII redacted from input",
        "Search for Python news and my email is john@corp.com")

    run("t3", "Layer 3 — HITL pauses before send_email, then approved",
        "Send an email to team@company.com about the sprint review.",
        approve=True)

    run("t4", "Layer 4 — safety check on normal output",
        "Explain what a for-loop is in Python.")
