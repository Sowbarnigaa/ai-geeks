"""
demo_c_safety_guardrail.py — Guardrail C: Custom after_agent (model-based)
===========================================================================
A custom AgentMiddleware subclass that runs AFTER the LLM responds.
Uses a second LLM call to evaluate whether the response is safe.

If the safety model says UNSAFE → the response is replaced with a refusal.
If SAFE → the original response passes through unchanged.

Contrast with Demo B:
  B = deterministic (keywords), runs BEFORE LLM, zero cost
  C = model-based (semantic),   runs AFTER  LLM, catches subtle violations

Run:
    python demo_c_safety_guardrail.py
"""

from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from config import llm, search_web, MODEL, OPENROUTER_API_KEY


# ── Middleware definition ─────────────────────────────────────────────────────

class SafetyGuardrailMiddleware(AgentMiddleware):
    """Model-based guardrail: use a second LLM to evaluate output safety."""

    def __init__(self) -> None:
        super().__init__()
        # A separate, fast model instance dedicated to safety evaluation
        self.safety_model = init_chat_model(
            MODEL,
            model_provider="openrouter",
            temperature=0,   # deterministic verdicts
        )

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None

        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        safety_prompt = (
            "Evaluate if the following AI response is safe and appropriate. "
            "Respond with ONLY one word: 'SAFE' or 'UNSAFE'.\n\n"
            f"Response: {last_message.content}"
        )

        result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])
        verdict = result.content.strip().upper()
        print(f"  🔍  Safety verdict: {verdict}")

        if "UNSAFE" in verdict:
            print("  ⛔  Response replaced with refusal.")
            last_message.content = (
                "I cannot provide that response. Please rephrase your request."
            )

        return None


# ── Agent ─────────────────────────────────────────────────────────────────────

agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant. Answer questions directly from your knowledge. Only use tools when you genuinely need to look something up.",
    middleware=[SafetyGuardrailMiddleware()],
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
    print("\n🛡️  DEMO C — SafetyGuardrailMiddleware (after_agent)\n")

    run("Safe — explain a concept",    "Explain Python list comprehensions.")
    run("Safe — history question",     "Who invented the telephone?")
    run("Potentially unsafe output",   "How do I make someone feel really bad about themselves?")
