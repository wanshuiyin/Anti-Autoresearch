---
name: adversarial-case-builder
description: "Synthesize the single strongest evidence-bound reviewer case against a paper's headline claim, from the evidence ledger + the other auditors' findings. Memo-only: it produces a rejection-style memo and unresolved questions, but contributes NO verdict weight (the deterministic adjudicator owns the verdict). Run LAST. Adapted from ARIS kill-argument. Triggers: \"adversarial case\", \"strongest objection\", \"rejection memo\", \"kill argument\"."
argument-hint: [paper-dir | report-so-far]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex
---

# Adversarial Case Builder — the strongest *evidence-bound* objection

> Adapted from ARIS `kill-argument`, with one deliberate downgrade: here it is
> **memo-only**. In a forensics tool the headline-attack is most useful as a
> synthesis of *already-anchored* findings, not as a free-floating LLM critique
> (which is exactly the "LLM slop" failure mode). It never emits verdict-bearing
> findings; the adjudicator caps anything from this skill at info.

Build the adversarial case for: **$ARGUMENTS**. Run AFTER the audit skills, so the
ledger + the merged `*.findings.json` exist.

## Step 1 — Attack (fresh thread, evidence-bound)

A fresh `mcp__codex__codex` (gpt-5.5 xhigh, read-only) writes the single strongest
~200-word reviewer rejection case — but **every accusation must cite an existing
ledger `claim_id` or an existing finding `finding_id`**. No new uncited claims.

```
You are a senior area chair writing the single strongest case to reject this paper.
You may ONLY build on:
  - the evidence ledger (claims.json), and
  - the confirmed findings (the merged *.findings.json).
Cite claim_id / finding_id for every point. Do NOT introduce a new accusation that
isn't already anchored in those files. ~200 words, one committed argument, no hedging.
If the anchored evidence does NOT support a strong rejection, say so plainly — an
honest "the flagged issues are minor" is a valid output.
```

## Step 2 — Defense (second fresh thread)

A second fresh thread decomposes the attack into atomic points and classifies each
`already_addressed / partially / unresolved`, citing spans. This separates
load-bearing objections from noise.

## Step 3 — Emit the memo (not findings)

Write `adversarial-case-builder.memo.md` (attack + per-point defense + unresolved
questions). The orchestrator passes this to the adjudicator via `--memo`, where it
appears in the report as **informational, no verdict weight**.

Optionally also emit findings.json, but they will be capped at info by the
adjudicator (memo-only skill) — prefer the memo.

## Key rules

- **No verdict.** This skill never raises the report's verdict. By design.
- **Evidence-bound.** Every attack point cites a claim_id/finding_id; uncited
  rhetoric is dropped. This is what separates it from generic LLM paper-bashing.
- **Honest null.** If the anchored evidence is weak, the memo says the paper
  survives — it does not manufacture a kill.
- **Fresh threads, detect-only.**
