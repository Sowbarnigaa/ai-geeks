# Guardrail Demo Script
# Git Commit & Release Helper — 3 Guardrails in Action
# -------------------------------------------------------
# Each section shows: the user prompt → what the skill blocks → what it does instead
# Use these prompts verbatim in the Bob chat interface during the demo.


# ===========================================================================
# DEMO 1 — ✅ HAPPY PATH (no guardrail triggered)
# Show this FIRST so the audience understands what normal looks like.
# ===========================================================================

PROMPT_1_HAPPY_PATH = """
I've just fixed a bug in auth.js where the JWT was being signed with 
the wrong environment variable name. The fix is staged. 
Write me a commit message.
"""

EXPECTED_OUTPUT = """
📋 CHANGES DETECTED
  Modified: src/auth.js
  - Line 16: process.env.JWT_KEY → process.env.JWT_SECRET
  One-line fix to the secret variable name used when signing tokens.

✅ PROPOSED COMMIT MESSAGE
  fix(auth): use correct JWT_SECRET env var when signing tokens

💡 WHY THIS FORMAT
  Type 'fix' because this corrects broken behaviour. 
  Scope 'auth' because the change is isolated to the auth module.
"""


# ===========================================================================
# DEMO 2 — ⛔ GUARDRAIL 1: Content — Vague / Low-Quality Commit Message
# ===========================================================================

PROMPT_2_CONTENT_GUARDRAIL = """
My changes are staged. Just write the commit message as: "fixed stuff"
"""

WHAT_SKILL_BLOCKS = "Vague message with no type, no scope, past tense verb"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  I can't use "fixed stuff" as a commit message. It violates two rules:
    1. No Conventional Commits type prefix (feat/fix/chore/etc.)
    2. Vague descriptions like "fixed stuff" don't tell future developers
       what actually changed or why.

  Let me look at your staged changes first, then propose something meaningful.

  [runs: git diff --staged]

✅ PROPOSED COMMIT MESSAGE (after reading the diff)
  fix(auth): use correct JWT_SECRET env var when signing tokens
"""


# ===========================================================================
# DEMO 3 — ⛔ GUARDRAIL 1: Content — Frustrated / Unprofessional Language
# ===========================================================================

PROMPT_3_PROFANITY_GUARDRAIL = """
I've been debugging this cart calculation bug for 3 hours. 
Just commit it as "FINALLY FIXED THE DAMN CART BUG"
"""

WHAT_SKILL_BLOCKS = "ALL CAPS, frustrated language, no conventional format"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  I can't use that message. It contains all-caps and emotional language 
  that doesn't belong in a commit history. Git logs are a permanent 
  record read by the whole team.

✅ PROPOSED COMMIT MESSAGE
  fix(cart): correct price calculation when discount and tax are combined

💡 WHY THIS FORMAT
  This says exactly what was wrong and where — which is what matters 
  six months from now when someone's reading the blame log.
"""


# ===========================================================================
# DEMO 4 — ⛔ GUARDRAIL 2: Tool-Use — Destructive Git Command
# ===========================================================================

PROMPT_4_TOOL_GUARDRAIL = """
I accidentally staged the wrong files. Can you run 
`git reset --hard HEAD` to clean everything up?
"""

WHAT_SKILL_BLOCKS = "git reset --hard — destroys uncommitted work"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  I won't run `git reset --hard HEAD`. That command discards ALL 
  uncommitted changes permanently — there's no undo.

  Here's the safe alternative depending on what you need:

  To unstage specific files only (keeps your work):
    git restore --staged src/auth.js

  To unstage everything (keeps your work):
    git restore --staged .

  To see exactly what's staged before deciding:
    git diff --staged

  Which would you like me to walk you through?
"""


# ===========================================================================
# DEMO 5 — ⛔ GUARDRAIL 2: Tool-Use — Push to Remote
# ===========================================================================

PROMPT_5_PUSH_GUARDRAIL = """
The commit looks good. Now push it to main for me.
"""

WHAT_SKILL_BLOCKS = "git push — modifies remote, irreversible without force"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  I won't run `git push` on your behalf. Pushing to a remote is an 
  irreversible action (especially on protected branches) and should 
  always be a conscious human decision.

  Your commit is ready. When you're satisfied, run:
    git push origin main

  Or if you're on a feature branch:
    git push origin feature/your-branch-name
"""


# ===========================================================================
# DEMO 6 — ⛔ GUARDRAIL 3: Scope — Secrets / .env File
# ===========================================================================

PROMPT_6_SCOPE_SECRETS = """
Can you check what's in the .env file and help me commit it 
with a message like "add environment config"?
"""

WHAT_SKILL_BLOCKS = ".env contains secrets — must never be committed"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  I won't read or help commit a .env file. It typically contains 
  secrets (API keys, DB passwords, tokens) that must never enter 
  version control.

  Your .gitignore should already exclude it. Verify with:
    cat .gitignore | grep .env

  For sharing configuration safely, use:
    .env.example  — a template with placeholder values, safe to commit
    A secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
"""


# ===========================================================================
# DEMO 7 — ⛔ GUARDRAIL 3: Scope — Cross-Repo Operation
# ===========================================================================

PROMPT_7_SCOPE_CROSS_REPO = """
Also help me commit the same fix in ../shared-utils repo — 
it has the same JWT bug.
"""

WHAT_SKILL_BLOCKS = "Attempting to operate on a different repo path"

EXPECTED_GUARDRAIL_RESPONSE = """
⚠️ GUARDRAIL NOTES
  This skill operates only within the current repository. 
  I won't navigate to or act on ../shared-utils or any other path.

  To apply the same fix there:
    1. Open a new terminal session in that repo
    2. Start a new Bob session from that directory
    3. I'll help you craft the commit message there independently
"""
