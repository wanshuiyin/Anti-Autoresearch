---
name: baseline-comparison-audit
description: "Audit the fairness and completeness of baseline comparisons: missing required SOTA baselines, undertuned/weak baselines, config mismatches between the proposed method and what it's compared against, wrong delta arithmetic, and 'outperforms' claims with overlapping error bars or no variance. Uses a per-domain baseline profile. Works at L0 (stated comparisons) and deepens at L2. Triggers: \"baseline audit\", \"missing baselines\", \"is the comparison fair\", \"baseline 误报\"."
argument-hint: [paper-dir | claims.json]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, mcp__codex__codex
---

# Baseline Comparison Audit — is the comparison fair and complete?

> Adapted from ARIS `paper-claim-audit` (scope + delta checks) plus a domain
> baseline profile. A favorite autoresearch shortcut: claim SOTA while omitting the
> obvious recent baseline, or compare against an undertuned one.

Audit baselines for: **$ARGUMENTS** (uses `claims.json`; needs the task/domain).

## Step 1 — Identify task + the expected baseline set

From the ledger's scope/method claims, determine the benchmark/task. Build the
**expected baseline set** for that task (the baselines a competent reviewer expects
in 2024–2026), using a domain profile + a quick `WebSearch` for "<benchmark> SOTA
<year> leaderboard". Record the expected set and its source.

> The domain profile is intentionally small in v0 (a few ML tasks). Where no
> profile exists, the skill still runs the *fairness* checks (Step 3) and marks the
> *completeness* check (Step 2) `needs_external_check` rather than guessing.

## Step 2 — Completeness (cross-model)

Send the paper's reported baseline list + the expected set to a fresh
`mcp__codex__codex` (gpt-5.5 xhigh, read-only). Findings:

- **HP-MISSING-BASELINE** (major; critical if the headline is a SOTA claim) — an
  expected/recent SOTA baseline is absent while "best/SOTA" is claimed. Evidence:
  the SOTA-claim span + the (present) baseline list. FP cases: concurrent/
  unavailable work, justified omission — set `false_positive_risk` accordingly.

## Step 3 — Fairness (cross-model + arithmetic)

```
For each head-to-head comparison in the ledger:
  - HP-WEAK-BASELINE : is the baseline given less compute/tuning/data, or run at
    unfavorable settings, vs the proposed method? config mismatch between compared
    rows?                                                          [major]
  - HP-SIG-OVERLAP   : is "outperforms/better" claimed where reported error bars
    overlap, or where NO variance / seed count is reported for a small gap? [minor→major]
  - delta arithmetic : re-verify every "improves by X%" against operands (this also
    runs deterministically in consistency-audit; cross-check).     [HP-DELTA-ERROR]
Each finding cites the ledger claim_id(s) + spans; describe a discrepancy to check.
```

At L2, deepen with the actual configs/result files (compare hyperparameters,
budgets, seeds between the proposed method and baselines).

## Emit + trace

Validate spans, write `baseline-comparison-audit.findings.json`, save traces. No
verdict here.

## Key rules

- **No domain profile ⇒ no guessed "missing baseline".** Mark `needs_external_check`.
- **Asymmetry is the signal** for weak baselines: unequal budget/tuning/data.
- **Small gap + no variance** is a flag, not proof — keep severity honest.
- **Detect-only.**
