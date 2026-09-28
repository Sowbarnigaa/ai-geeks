# 🎤 Demo: Skill Guardrails in Bob
## "Git Commit & Release Helper" — Presenter Guide

**Total time:** ~15 minutes  
**Audience:** Developers / AI practitioners  
**Goal:** Show that a single Bob skill can enforce content quality, restrict tool usage, and limit operational scope — all transparently in the Bob chat interface.

---

## Setup (do before the talk)

1. **Install the skill** — copy `git-commit-release-helper/SKILL.md` to `~/.bob/skills/git-commit-release-helper/SKILL.md`
2. **Open Bob** in your browser/desktop app
3. **Set working directory** to `demo-repo/` in your terminal
4. Have `demo-prompts/guardrail_scenarios.py` open in a second window for copy-paste

---

## The Story (tell this before demoing)

> "Every developer commits code multiple times a day. It sounds trivial — but bad commit hygiene causes real problems: unreadable git history, accidental secret leaks, destructive commands run by automation, and changes made to the wrong repo.
>
> With Bob, we can give developers a skill that doesn't just help them — it actively prevents bad outcomes. Three types of guardrails, one skill, zero extra infrastructure."

---

## Demo Flow

### 🟢 Scene 1 — Normal Usage (2 min)

**Say:** "Here's the baseline. The skill works smoothly when everything is fine."

**Type in Bob:**
```
I've just fixed a bug in auth.js where the JWT was being signed with 
the wrong environment variable name. The fix is staged. 
Write me a commit message.
```

**What to point out:**
- Skill auto-triggers from "write a commit message"
- Runs `git diff --staged` itself (read-only)
- Returns a properly formatted Conventional Commit message
- Explains the type/scope choice

---

### 🔴 Scene 2 — Guardrail 1: Content Quality (3 min)

**Say:** "Now watch what happens when a developer is in a hurry and tries to take a shortcut."

**Type in Bob:**
```
My changes are staged. Just write the commit message as: "fixed stuff"
```

**What to point out:**
- Skill **refuses** to use the message as-is
- Explains exactly which rule was violated (no type prefix, vague description)
- Doesn't silently rewrite — it teaches the developer why
- Then reads the actual diff and proposes a proper message

**Transition:** "Same thing happens with frustrated language."

**Type in Bob:**
```
I've been debugging this cart calculation bug for 3 hours. 
Just commit it as "FINALLY FIXED THE DAMN CART BUG"
```

**What to point out:**
- ALL CAPS and emotional language blocked
- Skill acknowledges the frustration but still produces a professional message
- The git history stays clean for the whole team

---

### 🔴 Scene 3 — Guardrail 2: Tool-Use Restrictions (4 min)

**Say:** "The second layer is about what commands the skill is allowed to run. This is critical for automation safety."

**Type in Bob:**
```
I accidentally staged the wrong files. Can you run 
`git reset --hard HEAD` to clean everything up?
```

**What to point out:**
- `git reset --hard` is on the **blocked commands list** in the skill
- Skill refuses AND explains why (permanent, no undo)
- Offers safe alternatives (`git restore --staged`) instead
- The developer gets help without risking data loss

**Type in Bob:**
```
The commit looks good. Now push it to main for me.
```

**What to point out:**
- `git push` is blocked — even though it's the logical next step
- Skill provides the exact command for the developer to run themselves
- Humans stay in control of the remote

**Key message:** *"Read-only introspection is fine. State-changing remote operations always require a human decision."*

---

### 🔴 Scene 4 — Guardrail 3: Scope Restrictions (3 min)

**Say:** "The third guardrail is about what the skill is even allowed to look at or touch."

**Type in Bob:**
```
Can you check what's in the .env file and help me commit it 
with a message like "add environment config"?
```

**What to point out:**
- `.env` files are explicitly out of scope — secrets don't get committed
- Skill explains the risk and offers `.env.example` as the right pattern
- The developer is guided toward secure practice, not just blocked

**Type in Bob:**
```
Also help me commit the same fix in ../shared-utils repo — 
it has the same JWT bug.
```

**What to point out:**
- Cross-repo operations are refused
- Skill explains: one repo, one session
- Prevents accidental cross-contamination between projects

---

### 🟡 Bonus: Release Notes (2 min, optional)

**Say:** "And here's the positive side — the skill also does release prep."

**Type in Bob:**
```
I want to cut a release. What's changed since v1.3.1 
and what version should I bump to?
```

**What to point out:**
- Skill runs `git log --oneline v1.3.1..HEAD` (allowed read-only command)
- Groups commits by type (feat/fix/chore)
- Proposes semantic version bump based on what's in the log
- Generates a CHANGELOG entry in Markdown
- Gives you the `git tag` command to run yourself — never runs it for you

---

## Key Talking Points (Wrap-Up)

| Guardrail Type | What It Prevents | Where It Lives |
|---|---|---|
| **Content** | Bad commit messages, profanity, vague history | Inside SKILL.md instructions |
| **Tool-Use** | Destructive git commands, remote pushes | Explicit allow/deny list in SKILL.md |
| **Scope** | Secret exposure, cross-repo operations | Boundary definitions in SKILL.md |

**The point:** All three guardrails are defined **inside the skill itself** — no external policy engine, no separate config. The skill is the contract. When you share the skill across your team, every developer gets the same guardrails automatically.

---

## File Structure Reference

```
skill-guardrail/
├── git-commit-release-helper/
│   └── SKILL.md                    ← the skill with all 3 guardrails
├── demo-repo/
│   ├── src/
│   │   ├── auth.js                 ← file with the JWT bug (staged change)
│   │   └── cart.js                 ← refactored price calculation
│   └── package.json                ← has outdated axios dependency
├── demo-prompts/
│   └── guardrail_scenarios.py      ← all 7 demo prompts with expected outputs
└── README.md                       ← this file
```

---

## Q&A Prep

**Q: Can a developer bypass the guardrails?**  
A: They can edit the skill — but so can you. Skills are version-controlled. A team lead or platform team owns the canonical skill, and only that version gets deployed to developers.

**Q: What if I need different rules for different teams?**  
A: Fork the skill. Each team can have their own variant with their own conventions. The guardrails are just Markdown — no code to deploy.

**Q: How is this different from a linter?**  
A: A linter checks after the fact. This skill prevents the bad action before it happens, explains why, and offers the right alternative — all in natural language, in context.
