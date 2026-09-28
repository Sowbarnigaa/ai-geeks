"""
Guardrails Demo — LangChain (Official Middleware API) + OpenRouter
===================================================================
Exact equivalent of https://docs.langchain.com/oss/python/langchain/guardrails

Demonstrates every guardrail pattern from the official docs:

  1. PIIMiddleware          – built-in PII redaction (email, credit card, IP)
  2. ContentFilterMiddleware – custom before_agent deterministic keyword block
  3. SafetyGuardrailMiddleware – custom after_agent model-based output check
  4. HumanInTheLoopMiddleware  – require human approval before sensitive tools
  5. Layered / combined        – all four stacked on one agent

Model: meta-llama/llama-3.1-8b-instruct:free  (free tier on OpenRouter)

Usage:
    export OPENROUTER_API_KEY="sk-or-..."
    python guardrails_demo.py
"""

import os
from typing import Any

# ── LangChain middleware imports (official API) ───────────────────────────────
from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    PIIMiddleware,
    HumanInTheLoopMiddleware,
    after_agent,
    before_agent,
    hook_config,
)
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.runtime import Runtime

# ─────────────────────────────────────────────────────────────────────────────
# 0.  Configure OpenRouter as the LLM backend
#     LangChain 1.x supports "openrouter" as a first-class provider.
#     ChatOpenRouter reads OPENROUTER_API_KEY from the environment, so we
#     ensure it is set before calling init_chat_model.
# ─────────────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "YOUR_OPENROUTER_API_KEY")
os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY   # ensure env is set
MODEL = "meta-llama/llama-3.1-8b-instruct"              # OpenRouter model slug

llm = init_chat_model(
    MODEL,
    model_provider="openrouter",
    temperature=0.7,
)

# ─────────────────────────────────────────────────────────────────────────────
# 1.  Demo tools the agent can call
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    # Stub — returns a canned answer so we don't need a real search API
    return f"[stub] Search results for: {query}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    # Stub — in production this would call an email API
    return f"[stub] Email sent to {to} with subject '{subject}'"


@tool
def delete_database(table: str) -> str:
    """Delete all rows from a database table (DANGEROUS)."""
    return f"[stub] Deleted all rows from {table}"


# ─────────────────────────────────────────────────────────────────────────────
# 2.  GUARDRAIL A  ── PIIMiddleware  (built-in, exact docs pattern)
#
#     Redact emails and mask credit cards in user INPUT;
#     block API-key-shaped strings with an exception.
# ─────────────────────────────────────────────────────────────────────────────

pii_agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant.",
    middleware=[
        # Redact emails in user input before sending to the model
        PIIMiddleware(
            "email",
            strategy="redact",
            apply_to_input=True,
        ),
        # Mask credit card numbers in user input
        PIIMiddleware(
            "credit_card",
            strategy="mask",
            apply_to_input=True,
        ),
        # Block anything that looks like an OpenAI/OpenRouter API key
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{20,}",   # custom regex detector
            strategy="block",
            apply_to_input=True,
        ),
        # Also redact IPs in the model's OUTPUT
        PIIMiddleware(
            "ip",
            strategy="redact",
            apply_to_output=True,
        ),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  GUARDRAIL B  ── Custom before_agent  (deterministic keyword filter)
#
#     Exact class-syntax pattern from the docs.
#     Blocks requests that match banned keywords before any LLM call.
# ─────────────────────────────────────────────────────────────────────────────

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
                print(f"  [ContentFilter] blocked keyword: '{keyword}'")
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


content_filter_agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant.",
    middleware=[
        ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware", "virus"]),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  GUARDRAIL C  ── Custom after_agent  (model-based output safety check)
#
#     Exact class-syntax pattern from the docs.
#     Uses a fast LLM to evaluate the agent's final response before it
#     reaches the user; replaces unsafe responses with a refusal.
# ─────────────────────────────────────────────────────────────────────────────

class SafetyGuardrailMiddleware(AgentMiddleware):
    """Model-based guardrail: use an LLM to evaluate response safety."""

    def __init__(self) -> None:
        super().__init__()
        # Use the same OpenRouter model as the safety evaluator
        self.safety_model = init_chat_model(
            MODEL,
            model_provider="openrouter",
            temperature=0,
        )

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not state["messages"]:
            return None

        from langchain_core.messages import AIMessage
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return None

        safety_prompt = (
            "Evaluate if the following AI response is safe and appropriate. "
            "Respond with ONLY 'SAFE' or 'UNSAFE'.\n\n"
            f"Response: {last_message.content}"
        )

        result = self.safety_model.invoke([{"role": "user", "content": safety_prompt}])
        verdict = result.content.strip().upper()
        print(f"  [SafetyGuardrail] verdict = {verdict}")

        if "UNSAFE" in verdict:
            last_message.content = (
                "I cannot provide that response. Please rephrase your request."
            )

        return None


safety_agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant.",
    middleware=[SafetyGuardrailMiddleware()],
)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  GUARDRAIL D  ── HumanInTheLoopMiddleware  (built-in, exact docs pattern)
#
#     Pauses execution and waits for human approval before running
#     sensitive tools.  Requires a checkpointer for state persistence.
# ─────────────────────────────────────────────────────────────────────────────
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

hitl_agent = create_agent(
    model=llm,
    tools=[search_web, send_email, delete_database],
    system_prompt="You are a helpful assistant.",
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email": True,       # require approval
                "delete_database": True,  # require approval
                "search_web": False,      # auto-approve
            }
        ),
    ],
    checkpointer=InMemorySaver(),          # required for interrupt/resume
)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  GUARDRAIL E  ── Layered / combined  (all four stacked, exact docs pattern)
# ─────────────────────────────────────────────────────────────────────────────

layered_agent = create_agent(
    model=llm,
    tools=[search_web, send_email],
    system_prompt="You are a helpful assistant.",
    middleware=[
        # Layer 1 — deterministic input filter (before agent)
        ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware"]),

        # Layer 2 — PII protection (input + output)
        # Combine input+output into one instance to avoid duplicate name clash
        PIIMiddleware("email", strategy="redact", apply_to_input=True, apply_to_output=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),

        # Layer 3 — human approval for sensitive tools
        HumanInTheLoopMiddleware(interrupt_on={"send_email": True}),

        # Layer 4 — model-based safety check (after agent)
        SafetyGuardrailMiddleware(),
    ],
    checkpointer=InMemorySaver(),
)


# ─────────────────────────────────────────────────────────────────────────────
# DEMO RUNNER
# ─────────────────────────────────────────────────────────────────────────────

SEP = "=" * 65


def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def run(agent, label: str, user_input: str, config: dict | None = None) -> str:
    print(f"\n  USER : {user_input}")
    print(f"  {'─'*55}")
    kwargs: dict = {"messages": [{"role": "user", "content": user_input}]}
    result = agent.invoke(kwargs, config or {})
    # extract the last AI message text
    messages = result.get("messages", [])
    reply = messages[-1].content if messages else "<no response>"
    print(f"  BOT  : {reply}")
    return reply


if __name__ == "__main__":
    print("\n🛡️  LANGCHAIN GUARDRAILS DEMO — exact patterns from the official docs\n")

    # ── A. PII Middleware ─────────────────────────────────────────────────────
    section("A. PIIMiddleware — redact / mask / block PII")
    run(pii_agent, "PII — email + credit card",
        "My email is john.doe@example.com and my card is 5105-1051-0510-5100")

    # ── B. Deterministic keyword filter ──────────────────────────────────────
    section("B. ContentFilterMiddleware (before_agent) — keyword block")
    run(content_filter_agent, "Blocked — contains 'hack'",
        "How do I hack into a database?")

    run(content_filter_agent, "Safe — normal question",
        "What is the capital of France?")

    # ── C. Model-based output safety ─────────────────────────────────────────
    section("C. SafetyGuardrailMiddleware (after_agent) — LLM output check")
    run(safety_agent, "Safe output",
        "Explain Python list comprehensions.")

    # ── D. Human-in-the-loop ─────────────────────────────────────────────────
    section("D. HumanInTheLoopMiddleware — approve / reject tool call")
    thread = {"configurable": {"thread_id": "demo-thread-1"}}

    print("\n  USER : Send an email to alice@example.com about the meeting")
    print(f"  {'─'*55}")
    result = hitl_agent.invoke(
        {"messages": [{"role": "user",
                       "content": "Send an email to alice@example.com about the meeting"}]},
        thread,
    )
    messages = result.get("messages", [])
    print(f"  BOT  : {messages[-1].content if messages else '<interrupted — awaiting human approval>'}")
    print()
    print("  [Human decision] → APPROVE the email tool call")
    # Resume with approval
    resumed = hitl_agent.invoke(
        Command(resume={"decisions": [{"type": "approve"}]}),
        thread,
    )
    resumed_msgs = resumed.get("messages", [])
    print(f"  BOT  : {resumed_msgs[-1].content if resumed_msgs else '<no response>'}")

    # ── E. Layered guardrails ────────────────────────────────────────────────
    section("E. Layered guardrails — all four stacked")
    run(layered_agent, "Blocked at layer 1 (keyword filter)",
        "How do I exploit a server vulnerability?",
        config={"configurable": {"thread_id": "layered-1"}})

    run(layered_agent, "PII redacted at layer 2",
        "Please search for info and email john@corp.com the results",
        config={"configurable": {"thread_id": "layered-2"}})

    print(f"\n{SEP}")
    print("  Demo complete.")
    print(SEP)
