"""
Guardrails AI Demo — FastAPI Server
====================================
Wraps the same guarded chat pipeline as demo.py behind a REST endpoint.

Start:
    uvicorn src.server:app --reload --port 8000

Endpoints:
    POST /chat          – guarded chat (input + output validation)
    GET  /health        – liveness check

Example curl:
    curl -s -X POST http://localhost:8000/chat \\
         -H "Content-Type: application/json" \\
         -d '{"prompt": "What is the capital of France?"}' | python -m json.tool
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Re-use the pipeline from demo.py
from demo import safe_chat

app = FastAPI(
    title="Guardrails AI Demo API",
    description=(
        "Demonstrates local Guardrails Hub validators "
        "(DetectJailbreak, ToxicLanguage, DetectPII, ValidLength) "
        "with OpenRouter as the LLM backend."
    ),
    version="1.0.0",
)


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000, description="User prompt")
    system_prompt: Optional[str] = Field(
        default="You are a helpful assistant.",
        description="Optional system-level instruction for the LLM.",
    )


class ChatResponse(BaseModel):
    status: str                          # "ok" | "blocked"
    blocked_at: Optional[str] = None    # "input" | "output" | null
    block_reason: Optional[str] = None
    response: Optional[str] = None      # safe, validated response
    pii_scrubbed: bool = False           # true when output PII was anonymised


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(body: ChatRequest):
    """
    Guarded chat pipeline:
      1. Validate user prompt (jailbreak + toxic check)
      2. Call LLM via OpenRouter
      3. Validate + sanitise response (PII scrub + length gate)
    Returns the safe response, or a 400 with the block reason.
    """
    result = safe_chat(body.prompt, body.system_prompt or "You are a helpful assistant.")

    if result.blocked_at:
        # Return 400 so callers get a clear HTTP signal
        raise HTTPException(
            status_code=400,
            detail={
                "status": "blocked",
                "blocked_at": result.blocked_at,
                "reason": result.block_reason,
            },
        )

    pii_scrubbed = result.raw_response != result.safe_response

    return ChatResponse(
        status="ok",
        response=result.safe_response,
        pii_scrubbed=pii_scrubbed,
    )
