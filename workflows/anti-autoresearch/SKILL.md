---
name: anti-autoresearch
description: "End-to-end integrity-forensics sweep of a research paper (especially autoresearch / AI-Scientist-style output): ingest → evidence ledger → fan out the auditor skills (consistency, citation, experiment, baseline) → deterministic adjudicator → reviewer-ready Integrity Forensics Report. Observability-aware (PDF-only L0 → repo+results L2). Detect-only. Triggers: \"anti-autoresearch\", \"integrity audit this paper\", \"forensic review\", \"审一篇投稿的诚信\"."
argument-hint: [paper-dir | pdf-path | arxiv-id]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, WebSearch, WebFetch, mcp__codex__codex, mcp__codex__codex-reply, mcp__mcp-dblp__search
---

# /anti-autoresearch — the orchestrator

Run a full substantive-integrity forensic pass on: **$ARGUMENTS**.

This is decision **support for a human reviewer / area chair** — it surfaces
span-anchored discrepancies to investigate. It is **not** an AI-text detector and
it does **not** judge misconduct. See `references/` for the contracts.

## Pipeline

```
[0] ingest        — resolve input to a working dir (arxiv-id → download source/PDF)
[1] evidence-ledger — artifact_manifest.json (+ observability level) + claims.json
[2] fan out auditors (each reads the ledger, emits <skill>.findings.json)
      consistency-audit            (always; flagship; deterministic + semantic)
      citation-forensics           (if citations present)
      baseline-comparison-audit    (if a comparison/SOTA claim is present)
      experiment-forensics         (L0/L1: info signals only · L2: full code audit)
[3] adversarial-case-builder       (memo only, evidence-bound, no verdict weight)
[4] adjudicate     — tools/adjudicate_findings.py → REPORT.md + report.json
```

## Step 0 — Ingest

Resolve `$ARGUMENTS` to a directory:
- a dir with `*.tex` → L1+ candidate; a lone PDF → extract text (`pdftotext -layout`)
  → L0; an arXiv id → fetch source if available (better spans) else the PDF.
- if a code repo / `results/` is present alongside → L2 candidate.

## Step 1 — Build the ledger (always first)

Invoke `/evidence-ledger`. This writes `artifact_manifest.json` (deriving the
observability level **L**) and `claims.json`. Everything downstream reads these.
Carry **L** forward — it caps every finding's severity.

## Step 2 — Fan out the auditors

Run the applicable skills (decide from the ledger's claim types):

| Skill | Run when | Adds |
|-------|----------|------|
| `/consistency-audit` | always | `consistency-audit.findings.json` (+ deterministic) |
| `/citation-forensics` | ≥1 `citation` claim | `citation-forensics.findings.json` |
| `/baseline-comparison-audit` | ≥1 comparison/scope SOTA claim | `baseline-comparison-audit.findings.json` |
| `/experiment-forensics` | always (depth scales with L) | `experiment-forensics.findings.json` |

Each is cross-model (codex, fresh threads) and span-anchored. Reviewer
independence + reviewer≠adjudicator hold throughout (`references/
reviewer-independence.md`). Fan-out is for breadth; the verdict is still the
deterministic adjudicator's.

## Step 3 — Adversarial memo (last, optional)

Invoke `/adversarial-case-builder` → `adversarial-case-builder.memo.md`. Memo only.

## Step 4 — Adjudicate (deterministic — the verdict)

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
python3 "$ROOT/tools/adjudicate_findings.py" \
    --findings *.findings.json \
    --paper-id <id> --observability-level <L> --taxonomy-version 0.1 \
    --memo "$(cat adversarial-case-builder.memo.md 2>/dev/null)" \
    --out report.json --md REPORT.md
```

The adjudicator applies the gates (span → observability → FP-risk → memo-only) and
computes `overall_verdict` ∈ {CLEAN_GIVEN_EVIDENCE, SOFT_FLAGS, HARD_FLAGS} by
fixed rules. No model is in the final decision.

## Step 5 — Present

Show the user `REPORT.md` (evidence table first, detail, adversarial memo,
limitations). Lead with the verdict + observability level, and state plainly what
could **not** be checked at this level.

## Key rules

- **Observability honesty.** Never present an L0 run as if it could see code; the
  report's limitations section says what was unverifiable.
- **Reviewer ≠ judge.** Skills propose findings; `adjudicate_findings.py` decides.
- **Detect-only, no accusation.** Output is "investigate this", never "this is fraud".
- **Reproducible.** Same artifacts → same ledger → same verdict.
