"""
demo_a_pii.py — Guardrail A: PIIMiddleware
==========================================
Built-in middleware that redacts / masks / blocks Personally Identifiable
Information BEFORE the user message reaches the LLM and AFTER the LLM responds.

Strategies:
  redact  → replaces with [REDACTED_EMAIL]
  mask    → partially obscures  e.g. ****-****-****-5100
  block   → raises an exception immediately
  hash    → replaces with a deterministic hash

Run:
    python demo_a_pii.py
"""

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

from config import llm, search_web

# ── Agent with PII guardrails ─────────────────────────────────────────────────
agent = create_agent(
    model=llm,
    tools=[search_web],
    system_prompt="You are a helpful assistant.",
    middleware=[
        # 1. Redact email addresses in user input
        PIIMiddleware("email", strategy="redact", apply_to_input=True),

        # 2. Mask credit card numbers in user input
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),

        # 3. Block API-key-shaped strings (custom regex detector)
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{20,}",
            strategy="block",
            apply_to_input=True,
        ),

        # 4. Redact IP addresses in the LLM's OUTPUT
        PIIMiddleware("ip", strategy="redact", apply_to_output=True),
    ],
)


def run(label: str, user_input: str) -> None:
    print(f"\n{'─'*55}")
    print(f"  TEST : {label}")
    print(f"  USER : {user_input}")
    print(f"{'─'*55}")
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
        reply = result["messages"][-1].content
        print(f"  BOT  : {reply}")
    except Exception as e:
        print(f"  ⛔  BLOCKED: {e}")


if __name__ == "__main__":
    print("\n🛡️  DEMO A — PIIMiddleware\n")

    run(
        "Email + credit card in message",
        "My email is john.doe@example.com and my card is 5105-1051-0510-5100",
    )

    run(
        "API key in message → blocked",
        "Here is my key: abcdefghijklmno",
    )

    run(
        "Normal message — no PII",
        "What is the capital of France?",
    )
