---
name: presentation-signals
description: "Surface-level signals a reviewer notices first: duplicate/near-identical tables, too-few or LLM-generated figures, page-padding, jargon-stuffing, and generic AI-flavored prose. AUXILIARY ONLY — these are weak, high-false-positive presentation signals, capped at minor by the adjudicator (never a HARD verdict) and NOT an AI-generation classifier. Use to add 'look closer' context to substantive findings. Triggers: \"presentation signals\", \"AI-flavor check\", \"surface check\", \"排版/AI味\"."
argument-hint: [paper-dir | claims.json]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex
---

# Presentation Signals — the surface tells (auxiliary, never a verdict)

> ⚠️ **This skill is deliberately weak by design.** A polished paper can be
> fraudulent and a rough paper can be honest, so surface signals must never drive a
> verdict. Everything here is emitted under skill `presentation-signals`, which the
> adjudicator **caps at `minor`** (`SURFACE_ONLY_SKILLS`) — at most `SOFT_FLAGS`,
> never `HARD_FLAGS`. This is **not an AI-text classifier**; for authorship
> detection use a dedicated tool (Pangram/GPTZero/Binoculars). Our job is only to
> add *"combine with the substantive findings and look closer"* context. See
> `references/hack-pattern-taxonomy.md` section F.

Run surface checks for: **$ARGUMENTS**. Motivated by what real reviewers flag first
("两张表一模一样", "图还是大模型生成的", "就这还没写满9页", "堆砌名词").

## Step 1 — Deterministic surface check (no LLM)

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
python3 "$ROOT/tools/check_presentation.py" --ledger claims.json \
    --out presentation-signals.deterministic.findings.json
```

Catches `HP-DUP-TABLE` (two tables with identical numeric content) objectively from
the ledger's table cells.

## Step 2 — Semantic surface pass (cross-model, optional, needs the PDF)

The rest are judgment calls. A fresh `mcp__codex__codex` (gpt-5.5, read-only) gets
the rendered PDF + the ledger and is asked for **gross** cases only, each
span-anchored, each tagged `false_positive_risk: high`:

```
You are checking PRESENTATION signals only — NOT whether the paper is AI-written and
NOT whether it is fraudulent. Flag only blatant cases, each with a span/figure ref.
For each, emit a finding (schemas/finding.schema.json, skill:"presentation-signals",
severity:"minor", false_positive_risk:"high"):
  - HP-THIN-FLOAT   : a full-length paper with almost no figures/tables while
                      claiming broad empirical results.
  - HP-LLM-FIGURE   : a "figure" that is a generated illustration, not a real
                      plot/diagram of results.
  - HP-PAGE-PADDING : oversized floats / repeated content / vacuous filler to reach
                      (or conspicuously miss) the page limit.
  - HP-JARGON-STUFF : dense term-stuffing where the argument carries no content.
  - HP-AI-FLAVOR    : unedited generic LLM prose — GROSS cases only. This is the
                      most FP-prone signal; if in doubt, do NOT flag.
Do not speculate about authorship. Do not call anything fraud. If nothing is
blatant, return an empty list — that is the expected output for most papers.
```

## Step 3 — Validate + emit

Validate spans against the ledger / source, merge with the deterministic findings,
write `presentation-signals.findings.json`. The adjudicator caps everything at
`minor`. No verdict here.

## Key rules

- **Auxiliary only.** These never raise the verdict beyond `SOFT_FLAGS`. They are
  context for the substantive findings, not standalone evidence.
- **Not authorship detection.** Never label a paper "AI-generated" or imply
  misconduct from surface signals.
- **Default to silence.** Most papers should produce few or zero surface findings;
  an empty list is the common, correct output.
- **Detect-only.**
