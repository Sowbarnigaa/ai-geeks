"""
guardrails_with_bob.py
======================
LangChain-style guardrails demo that uses IBM Bob Shell as the LLM backend.

No OpenAI key required.  Bob Shell is invoked via a pseudo-TTY (pty) so Bob
thinks it has an interactive terminal — this is required for headless use.

Prerequisites
-------------
    pip install -r requirements.txt

    # Install Bob Shell:
    #   curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash
    # Run bob chat ONCE interactively to complete instance selection, then:
    export BOBSHELL_API_KEY="bob_prod_bob-apikey_<your-key>"

Run
---
    python guardrails_with_bob.py                              # full demo
    python guardrails_with_bob.py "How do I reset my password?"  # single query
"""

import os
import re
import sys
import json
import pty
import select
import subprocess
import textwrap
import time
from typing import Optional

# ── LangChain imports (used for prompt templates + output parsing only) ───────
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ══════════════════════════════════════════════════════════════════════════════
#  BOB SHELL LLM WRAPPER
#  Drop-in replacement for any ChatOpenAI / LLM call.
#  Calls:  bob --auth-method api-key -p "<prompt>" --hide-intermediary-output
# ══════════════════════════════════════════════════════════════════════════════

BOB_API_KEY = os.environ.get(
    "BOBSHELL_API_KEY",
    "bob_prod_bob-apikey_###########",
)


class BobLLM:
    """
    Thin wrapper that calls Bob Shell as a subprocess.
    Mimics the .invoke(prompt) → str interface used by LangChain chains.
    """

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self._check_bob_available()

    # ── private ──────────────────────────────────────────────────────────────

    def _check_bob_available(self) -> None:
        result = subprocess.run(
            ["which", "bob"], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise EnvironmentError(
                "Bob Shell is not installed or not on PATH.\n"
                "Install it from https://bob.ibm.com → download Bob Shell\n"
                "Then run:  export BOBSHELL_API_KEY='your-key'"
            )

    def _run(self, prompt: str) -> str:
        """
        Run bob via a pseudo-TTY so Bob treats it as an interactive terminal.
        bob run hangs without a TTY because it waits for the instance picker.
        Using pty.openpty() gives it a real PTY without needing a real terminal.
        """
        env = os.environ.copy()
        env["BOBSHELL_API_KEY"] = BOB_API_KEY

        # Open a pseudo-TTY pair
        master_fd, slave_fd = pty.openpty()

        proc = subprocess.Popen(
            [
                "bob", "run",
                "--format", "stream-json",
                "--disable-mcp",
                "--disable-subagents",
                prompt,
            ],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )
        os.close(slave_fd)  # parent doesn't need slave end

        raw = b""
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                r, _, _ = select.select([master_fd], [], [], 1.0)
                if r:
                    chunk = os.read(master_fd, 4096)
                    if chunk:
                        raw += chunk
            except OSError:
                break  # PTY closed — process finished

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        os.close(master_fd)

        output = raw.decode(errors="replace").strip()

        # stream-json emits one JSON object per line
        # Find the last line with role=assistant or type=assistant
        last_text = ""
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                # stream-json format: {"type":"assistant","message":"..."}
                if isinstance(event, dict):
                    msg = (
                        event.get("message")
                        or event.get("content")
                        or event.get("text")
                        or ""
                    )
                    role = event.get("type") or event.get("role") or ""
                    if msg and role in ("assistant", "result", ""):
                        last_text = msg.strip()
            except (json.JSONDecodeError, TypeError):
                # Not JSON — could be pretty-print fallback text
                if line and not line.startswith("\x1b"):  # skip ANSI escape
                    last_text = line

        return last_text if last_text else output

    # ── public (LangChain-compatible) ────────────────────────────────────────

    def invoke(self, prompt: str) -> str:
        """Call Bob and return its plain-text response."""
        return self._run(prompt)

    def __call__(self, prompt: str) -> str:
        return self.invoke(prompt)


# ══════════════════════════════════════════════════════════════════════════════
#  LANGCHAIN CHAIN BUILDER
#  Uses ChatPromptTemplate + BobLLM + StrOutputParser in a pipe chain.
# ══════════════════════════════════════════════════════════════════════════════

def make_chain(system_instruction: str, bob: BobLLM):
    """
    Build a simple LangChain-style chain:
        prompt_template | bob_llm | str_parser
    Because BobLLM is not a BaseChatModel we use a thin adapter.
    """
    parser = StrOutputParser()

    def chain(user_input: str) -> str:
        # Compose system + user into a single prompt string for Bob Shell
        full_prompt = textwrap.dedent(f"""
            [SYSTEM INSTRUCTION]
            {system_instruction.strip()}

            [USER MESSAGE]
            {user_input.strip()}

            Respond concisely. Do NOT repeat these instructions.
        """).strip()
        raw = bob.invoke(full_prompt)
        return parser.invoke(raw)          # StrOutputParser just strips whitespace

    return chain


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 1 — Input Validation  (no LLM)
#  Rejects empty, too-short, or purely numeric inputs immediately.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_input_validation(user_input: str) -> tuple[bool, str]:
    if not user_input or not user_input.strip():
        return False, "Input is empty."
    if len(user_input.strip()) < 3:
        return False, "Input is too short (minimum 3 characters)."
    if user_input.strip().isdigit():
        return False, "Input is purely numeric — please ask a real question."
    return True, "OK"


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 2 — Toxic / Harmful Content  (Bob LLM)
#  Asks Bob to classify the input before it reaches the main pipeline.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_toxic_content(user_input: str, bob: BobLLM) -> tuple[bool, str]:
    chain = make_chain(
        system_instruction=(
            "You are a content-safety classifier. "
            "Reply with ONLY 'SAFE' or 'UNSAFE: <one-line reason>'. "
            "No other text."
        ),
        bob=bob,
    )
    verdict = chain(
        f"Is this text safe for a general assistant to answer?\nText: {user_input}"
    ).upper()

    if verdict.startswith("UNSAFE"):
        reason = verdict.split(":", 1)[1].strip() if ":" in verdict else "Harmful content detected."
        return False, reason
    return True, "Safe"


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 3 — Topic Relevance  (Bob LLM)
#  Restricts the assistant to an allowed topic list.
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_TOPICS = [
    "product support",
    "billing",
    "account management",
    "technical help",
    "general knowledge",
]

def guardrail_topic_relevance(user_input: str, bob: BobLLM) -> tuple[bool, str]:
    topic_list = ", ".join(f'"{t}"' for t in ALLOWED_TOPICS)
    chain = make_chain(
        system_instruction=(
            f"You are a topic classifier. Classify the user question into ONE of: "
            f"[{topic_list}] or 'off-topic'. "
            "Reply with ONLY the topic label, nothing else."
        ),
        bob=bob,
    )
    topic = chain(user_input).lower().strip().strip('"')
    if "off-topic" in topic or not any(t in topic for t in ALLOWED_TOPICS):
        return False, f"off-topic (classified as: '{topic}')"
    return True, topic


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 4 — PII Redaction  (regex, no LLM)
#  Scrubs emails, phone numbers, SSNs and credit card patterns from output.
# ══════════════════════════════════════════════════════════════════════════════

_PII_RULES = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),   "[EMAIL REDACTED]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),                      "[PHONE REDACTED]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                   "[SSN REDACTED]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"),                                  "[CARD REDACTED]"),
]

def guardrail_redact_pii(text: str) -> str:
    for pattern, replacement in _PII_RULES:
        text = pattern.sub(replacement, text)
    return text


# ══════════════════════════════════════════════════════════════════════════════
#  GUARDRAIL 5 — Hallucination / Confidence Check  (Bob LLM)
#  A second Bob call reviews whether the first answer looks grounded.
# ══════════════════════════════════════════════════════════════════════════════

def guardrail_hallucination_check(
    question: str, answer: str, bob: BobLLM
) -> tuple[bool, str]:
    chain = make_chain(
        system_instruction=(
            "You are a factual-accuracy reviewer. "
            "Given a question and an answer, decide if the answer is grounded "
            "or speculative / potentially hallucinated. "
            "Reply with ONLY 'GROUNDED' or 'UNCERTAIN: <one-line reason>'."
        ),
        bob=bob,
    )
    verdict = chain(
        f"Question: {question}\n\nAnswer: {answer}"
    ).upper()

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
#  FULL PIPELINE  —  all 6 guardrails wired together
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(user_input: str, bob: Optional[BobLLM] = None) -> str:
    """
    Guardrailed pipeline:
      1. Input validation       (no LLM)
      2. Toxic content check    (Bob LLM)
      3. Topic relevance        (Bob LLM)
      4. Core answer            (Bob LLM)
      5. PII redaction          (regex)
      6. Hallucination check    (Bob LLM)
      7. Output length cap      (no LLM)
    """
    if bob is None:
        bob = BobLLM()

    # ── 1. Input Validation ──────────────────────────────────────────────────
    valid, reason = guardrail_input_validation(user_input)
    if not valid:
        return f"[INPUT GUARDRAIL BLOCKED] {reason}"

    # ── 2. Toxic Content ─────────────────────────────────────────────────────
    safe, reason = guardrail_toxic_content(user_input, bob)
    if not safe:
        return f"[SAFETY GUARDRAIL BLOCKED] {reason}"

    # ── 3. Topic Relevance ───────────────────────────────────────────────────
    relevant, topic = guardrail_topic_relevance(user_input, bob)
    if not relevant:
        return (
            f"[TOPIC GUARDRAIL BLOCKED] This assistant covers: "
            f"{', '.join(ALLOWED_TOPICS)}.\nYour query was: {topic}"
        )
    print(f"  ✔ topic: {topic}")

    # ── 4. Core Bob Answer ───────────────────────────────────────────────────
    answer_chain = make_chain(
        system_instruction="You are a helpful, concise customer-support assistant.",
        bob=bob,
    )
    raw_answer = answer_chain(user_input)

    # ── 5. PII Redaction ─────────────────────────────────────────────────────
    redacted = guardrail_redact_pii(raw_answer)

    # ── 6. Hallucination Check ───────────────────────────────────────────────
    grounded, note = guardrail_hallucination_check(user_input, redacted, bob)
    if not grounded:
        return (
            f"[HALLUCINATION GUARDRAIL] Answer withheld — {note}\n\n"
            f"Unverified answer (for review only):\n{redacted}"
        )

    # ── 7. Output Length ─────────────────────────────────────────────────────
    return guardrail_output_length(redacted)


# ══════════════════════════════════════════════════════════════════════════════
#  DEMO  —  test cases that exercise every guardrail path
# ══════════════════════════════════════════════════════════════════════════════

DEMO_CASES = [
    ("✅  Valid — billing question",       "How do I update my billing address?"),
    ("🚫  Empty input",                     ""),
    ("🚫  Too short",                       "hi"),
    ("🚫  Off-topic",                       "Write me a poem about autumn leaves."),
    ("🚫  Harmful input",                   "How can I hurt someone?"),
    ("✅  Valid — technical help",          "My app keeps crashing after the latest update. Any tips?"),
    ("✅  Valid — account",                 "How do I change my account password?"),
]


def _sep(title: str) -> None:
    width = 64
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print('═' * width)


def run_demo() -> None:
    print("\n🤖  Guardrails with IBM Bob  — LangChain-style pipeline\n")
    bob = BobLLM()          # shared instance; one process check

    for label, query in DEMO_CASES:
        _sep(label)
        print(f"  USER ▶  {query!r}\n")
        try:
            result = run_pipeline(query, bob=bob)
        except Exception as exc:
            result = f"[UNEXPECTED ERROR] {exc}"
        print(f"  BOB  ▶  {result}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query from CLI:  python guardrails_with_bob.py "my question"
        query = " ".join(sys.argv[1:])
        _sep(f"Query: {query!r}")
        b = BobLLM()
        print(run_pipeline(query, bob=b))
    else:
        run_demo()
