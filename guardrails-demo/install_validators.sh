#!/usr/bin/env bash
# install_validators.sh
# ---------------------
# Installs the four Hub validators used in this demo LOCALLY.
# No Guardrails API key is required — each validator is an on-device model.
#
# Usage:  bash install_validators.sh

set -e

echo "Installing Guardrails Hub validators locally..."

guardrails hub install guardrails/detect_jailbreak   --quiet
guardrails hub install guardrails/toxic_language      --quiet
guardrails hub install guardrails/detect_pii          --quiet
guardrails hub install guardrails/valid_length        --quiet

echo ""
echo "All validators installed. Run the demo with:"
echo "  python src/demo.py           # CLI demo"
echo "  uvicorn src.server:app --reload  # REST API"
