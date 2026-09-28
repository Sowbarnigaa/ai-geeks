"""
demo_d_human_in_the_loop.py — Guardrail D: HumanInTheLoopMiddleware
====================================================================
Built-in middleware that PAUSES the agent before executing a sensitive tool
and waits for a human to approve or reject the action.

How it works:
  1. Agent decides to call a tool (e.g. send_email)
  2. Middleware interrupts → agent is suspended
  3. Human reviews and sends Command(resume={"decisions": [{"type": "approve"}]})
     or                        Command(resume={"decisions": [{"type": "reject"}]})
  4. Agent resumes from the checkpoint

Requires a checkpointer (InMemorySaver) so state is preserved across the interrupt.

Run:
    python demo_d_human_in_the_loop.py
"""

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from config import llm, search_web, send_email, delete_database


# ── Agent ─────────────────────────────────────────────────────────────────────

agent = create_agent(
    model=llm,
    tools=[search_web, send_email, delete_database],
    system_prompt="You are a helpful assistant.",
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_email":      True,   # ← pause & wait for approval
                "delete_database": True,   # ← pause & wait for approval
                "search_web":      False,  # ← auto-approve, no pause
            }
        ),
    ],
    checkpointer=InMemorySaver(),   # required: preserves state across interrupt
)


# ── Demo runner ───────────────────────────────────────────────────────────────

def run_with_approval(thread_id: str, user_input: str, approve: bool = True) -> None:
    print(f"\n{'─'*55}")
    print(f"  USER : {user_input}")
    print(f"{'─'*55}")

    config = {"configurable": {"thread_id": thread_id}}

    # Step 1 — invoke; agent will pause before the sensitive tool
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_input}]},
        config,
    )
    messages = result.get("messages", [])
    last = messages[-1].content if messages else ""
    if last:
        print(f"  BOT  : {last}")
    else:
        print("  ⏸   Agent paused — awaiting human decision...")

    # Step 2 — human decides
    decision = "approve" if approve else "reject"
    print(f"\n  👤  Human decision: {decision.upper()}")

    # Step 3 — resume
    resumed = agent.invoke(
        Command(resume={"decisions": [{"type": decision}]}),
        config,
    )
    resumed_msgs = resumed.get("messages", [])
    final = resumed_msgs[-1].content if resumed_msgs else "<no response>"
    print(f"  BOT  : {final}")


if __name__ == "__main__":
    print("\n🛡️  DEMO D — HumanInTheLoopMiddleware\n")

    # Case 1: user approves the email
    run_with_approval(
        thread_id="thread-approve",
        user_input="Send an email to alice@example.com about tomorrow's meeting.",
        approve=True,
    )

    # Case 2: user rejects the email
    run_with_approval(
        thread_id="thread-reject",
        user_input="Send an email to bob@example.com with the quarterly report.",
        approve=False,
    )

    # Case 3: safe tool (search_web) — no interrupt at all
    print(f"\n{'─'*55}")
    print("  TEST : Safe tool (search_web) — no interrupt")
    print(f"{'─'*55}")
    config = {"configurable": {"thread_id": "thread-safe"}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Search for Python tutorials."}]},
        config,
    )
    msgs = result.get("messages", [])
    print(f"  BOT  : {msgs[-1].content if msgs else '<no response>'}")
