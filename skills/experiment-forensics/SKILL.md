---
name: experiment-forensics
description: "Audit experiment integrity when code/results are available (L2): fake ground truth, score self-normalization, phantom results (numbers with no backing file), dead/uncalled metric code, and scope inflation. When only the PDF is available (L0), emits the same patterns as info-level 'could-not-verify' risk signals — never asserts fraud from a PDF. Span-anchored, cross-model. Triggers: \"experiment forensics\", \"audit the results\", \"check the eval code\", \"实验诚实度\"."
argument-hint: [paper-dir | repo-dir]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex
---

# Experiment Forensics — are the reported results what the code computes?

> Adapted from ARIS `experiment-audit` (#57/#131). The original audits *your own*
> experiment; this audits a *third party's*. The crucial reframe: at L0/L1 (no
> code) these patterns are **not decidable** — they appear only as info-level
> "could-not-verify" signals. Code-level fraud requires L2.

Audit for: **$ARGUMENTS**. Read `artifact_manifest.json` to confirm the level.

## If observability level < 2 (no repo + results)

Do **not** assert any experiment-integrity fraud. Emit at most info-level signals
the human should chase IF a repo becomes available, each with
`observability_level_required: 2` (the adjudicator keeps them at info):

- 0.99+/100% scores, suspiciously round numbers, no seeds / error bars / variance.
- "comprehensive/SOTA/robust" with a thin reported scope.

These overlap with `consistency-audit` scope checks — defer to it for L0 scope, and
only add the *"needs code to verify"* note here.

## If observability level == 2 (repo + results present)

Collect paths (do NOT summarize their contents), then send to a fresh
`mcp__codex__codex` (gpt-5.5 xhigh, `sandbox: read-only`, `cwd` = repo). The
reviewer reads the eval code line by line and proposes findings. Checklist:

```
A. Ground-truth provenance  : is "reference/target/GT" loaded from the DATASET, or
   derived from MODEL OUTPUTS and reported as performance (not labeled proxy)?
                                                                  [HP-FAKE-GT, critical]
B. Score normalization      : any metric divided by max/min/mean of the model's OWN
   output to approach 1.0? raw scores shown?                      [HP-SELF-NORM, critical]
C. Result existence         : does each paper number map to a real key in a real
   result file? (cite the ledger claim + the file/key checked)    [HP-PHANTOM-RESULT, critical]
D. Dead metric code         : metric defined but never called / never in any result.[HP-DEAD-METRIC, major]
E. Scope (verified)         : how many datasets/seeds/configs were ACTUALLY run vs
   the paper's scope language?                                    [HP-SCOPE-INFLATE, major]

Output findings (schemas/finding.schema.json) with observability_level_required:2,
each citing a ledger claim_id + the exact code/file:line evidence span. Describe a
discrepancy, never an accusation. Set false_positive_risk honestly (labeled
synthetic_proxy and self-supervised-by-design are NOT fraud).
```

Cross-reference each code-level finding back to the paper claim it undermines (via
`claim_id`), so the report can show "this number ↔ this code problem".

## Emit + trace

Validate spans against the ledger / source files, write
`experiment-forensics.findings.json`, save traces. No verdict here.

## Key rules

- **L0/L1 ⇒ no fraud verdicts.** Only `consistency-audit`-style internal checks and
  info-level "needs code" signals. This is the honesty backbone.
- **Labeled proxies are legitimate.** `synthetic_proxy` / self-supervised-by-design
  are not fraud; do not flag them as such.
- **Executor collects paths; the reviewer judges the code.** Reviewer independence.
- **Detect-only.**
