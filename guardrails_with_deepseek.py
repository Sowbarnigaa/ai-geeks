"""
guardrails_with_deepseek.py
============================
LangChain guardrails demo using DeepSeek API (OpenAI-compatible).
No Bob Shell required — runs standalone with pip install only.

Prerequisites
-------------
    pip install langchain-openai langchain-core

Run
---
    python guardrails_with_deepseek.py                        # full demo
    python guardrails_with_deepseek.py "How do I reset my password?"  # single query
"""

import os
import re
import sys
import textwrap
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── DeepSeek API config (OpenAI-compatible) ───────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get(
    "DEEPSEEK_API_KEY",
    "sk-###########",
)

def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://api.deepseek.com",
        api_key=DEEPSEEK_API_KEY,
        model="deepseek-chat",
        temperature=0,
    )


# ── Chain builder ─────────────────────────────────────────────────────────────

def make_chain(system_instruction: str, llm: ChatOpenAI):
    """
    Build a simple LangChain chain:
        prompt_template | llm | str_output_parser
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instruction),
        ("human", "{input}"),
    ])
    return prompt | llm | StrOutputParser()


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 1 — Input Validation  (no LLM, instant)
#  Rejects empty, too-short, or purely numeric inputs.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_input_validation(user_input: str) -> tuple[bool, str]:
    if not user_input or not user_input.strip():
        return False, "Input is empty."
    if len(user_input.strip()) < 3:
        return False, "Input too short (minimum 3 characters)."
    if user_input.strip().isdigit():
        return False, "Input is purely numeric — please ask a real question."
    return True, "OK"


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 2 — Toxic / Harmful Content  (LLM judge)
#  Asks DeepSeek to classify before reaching the main pipeline.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_toxic_content(user_input: str, llm: ChatOpenAI) -> tuple[bool, str]:
    chain = make_chain(
        system_instruction=(
            "You are a content-safety classifier. "
            "Reply with ONLY 'SAFE' or 'UNSAFE: <one-line reason>'. "
            "No other text."
        ),
        llm=llm,
    )
    verdict = chain.invoke({"input": f"Is this text safe?\nText: {user_input}"}).strip().upper()
    if verdict.startswith("UNSAFE"):
        reason = verdict.split(":", 1)[1].strip() if ":" in verdict else "Harmful content detected."
        return False, reason
    return True, "Safe"


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 3 — Topic Relevance  (LLM classifier)
#  Restricts the assistant to allowed topics.
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_TOPICS = [
    "product support",
    "billing",
    "account management",
    "technical help",
    "general knowledge",
]

def guardrail_topic_relevance(user_input: str, llm: ChatOpenAI) -> tuple[bool, str]:
    topic_list = ", ".join(f'"{t}"' for t in ALLOWED_TOPICS)
    chain = make_chain(
        system_instruction=(
            f"You are a topic classifier. Classify the user question into ONE of: "
            f"[{topic_list}] or 'off-topic'. "
            "Reply with ONLY the topic label, nothing else."
        ),
        llm=llm,
    )
    topic = chain.invoke({"input": user_input}).lower().strip().strip('"')
    if "off-topic" in topic or not any(t in topic for t in ALLOWED_TOPICS):
        return False, f"off-topic (classified as: '{topic}')"
    return True, topic


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 4 — PII Redaction  (regex, no LLM)
#  Scrubs emails, phone numbers, SSNs and credit card patterns from output.
# ══════════════════════════════════════════════════════════════════════════════

_PII_RULES = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  "[EMAIL REDACTED]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),                    "[PHONE REDACTED]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                 "[SSN REDACTED]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"),                                "[CARD REDACTED]"),
]

def guardrail_redact_pii(text: str) -> str:
    for pattern, replacement in _PII_RULES:
        text = pattern.sub(replacement, text)
    return text


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 5 — Hallucination / Confidence Check  (LLM judge)
#  A second DeepSeek call reviews whether the answer looks grounded.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_hallucination_check(
    question: str, answer: str, llm: ChatOpenAI
) -> tuple[bool, str]:
    chain = make_chain(
        system_instruction=(
            "You are a factual-accuracy reviewer. "
            "Given a question and an answer, decide if the answer is grounded "
            "or speculative/hallucinated. "
            "Reply with ONLY 'GROUNDED' or 'UNCERTAIN: <one-line reason>'."
        ),
        llm=llm,
    )
    verdict = chain.invoke({
        "input": f"Question: {question}\n\nAnswer: {answer}"
    }).strip().upper()

    if verdict.startswith("UNCERTAIN"):
        note = verdict.split(":", 1)[1].strip() if ":" in verdict else "Answer may be unreliable."
        return False, note
    return True, "Grounded"


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 6 — Output Length Cap  (no LLM)
# ══════════════════════════════════════════════════════════════════════════════

MAX_OUTPUT_CHARS = 1500

def guardrail_output_length(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[... response truncated by output guardrail ...]"
    return text


# ══════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE  —  all guardrails wired together
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(user_input: str, llm: Optional[ChatOpenAI] = None) -> str:
    """
    Guardrailed pipeline:
      1. Input validation       (no LLM)
      2. Toxic content check    (LLM judge)
      3. Topic relevance        (LLM classifier)
      4. Core answer            (LLM)
      5. PII redaction          (regex)
      6. Hallucination check    (LLM judge)
      7. Output length cap      (no LLM)
    """
    if llm is None:
        llm = make_llm()

    # ── 1. Input Validation ──────────────────────────────────────────────────
    valid, reason = guardrail_input_validation(user_input)
    if not valid:
        return f"[INPUT GUARDRAIL BLOCKED] {reason}"

    # ── 2. Toxic Content ─────────────────────────────────────────────────────
    safe, reason = guardrail_toxic_content(user_input, llm)
    if not safe:
        return f"[SAFETY GUARDRAIL BLOCKED] {reason}"

    # ── 3. Topic Relevance ───────────────────────────────────────────────────
    relevant, topic = guardrail_topic_relevance(user_input, llm)
    if not relevant:
        return (
            f"[TOPIC GUARDRAIL BLOCKED] This assistant covers: "
            f"{', '.join(ALLOWED_TOPICS)}.\nYour query was classified as: {topic}"
        )
    print(f"  ✔ topic classified as: {topic}")

    # ── 4. Core Answer ───────────────────────────────────────────────────────
    answer_chain = make_chain(
        system_instruction="You are a helpful, concise customer-support assistant.",
        llm=llm,
    )
    raw_answer = answer_chain.invoke({"input": user_input})

    # ── 5. PII Redaction ─────────────────────────────────────────────────────
    redacted = guardrail_redact_pii(raw_answer)

    # ── 6. Hallucination Check ───────────────────────────────────────────────
    grounded, note = guardrail_hallucination_check(user_input, redacted, llm)
    if not grounded:
        return (
            f"[HALLUCINATION GUARDRAIL] Answer withheld — {note}\n\n"
            f"Unverified answer (for review only):\n{redacted}"
        )

    # ── 7. Output Length ─────────────────────────────────────────────────────
    return guardrail_output_length(redacted)


# ══════════════════════════════════════════════════════════════════════════════
#  DEMO  —  test cases exercising every guardrail path
# ══════════════════════════════════════════════════════════════════════════════

DEMO_CASES = [
    ("✅  Valid — billing question",   "How do I update my billing address?"),
    ("🚫  Empty input",                ""),
    ("🚫  Too short",                  "hi"),
    ("🚫  Off-topic",                  "Write me a poem about autumn leaves."),
    ("🚫  Harmful input",              "How can I hurt someone?"),
    ("✅  Valid — technical help",     "My app keeps crashing after the latest update. Any tips?"),
    ("✅  Valid — account",            "How do I change my account password?"),
]


def _sep(title: str) -> None:
    width = 64
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print("═" * width)


def run_demo() -> None:
    print("\n🛡  Guardrails with DeepSeek  — LangChain pipeline\n")
    llm = make_llm()

    for label, query in DEMO_CASES:
        _sep(label)
        print(f"  USER  ▶  {query!r}\n")
        try:
            result = run_pipeline(query, llm=llm)
        except Exception as exc:
            result = f"[UNEXPECTED ERROR] {exc}"
        print(f"  AGENT ▶  {result}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        _sep(f"Query: {query!r}")
        print(run_pipeline(query))
    else:
        run_demo()
