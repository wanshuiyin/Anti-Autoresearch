---
name: evidence-ledger
description: "Build the deterministic evidence ledger (artifact manifest + claims.json) that every other Anti-Autoresearch auditor reads. Detects available artifacts, derives the observability level, and extracts span-anchored claims (numbers, comparisons, scope, citations, captions, table cells) from LaTeX/PDF. Use FIRST, before any audit skill. Triggers: \"build the ledger\", \"extract claims\", \"prep for integrity audit\"."
argument-hint: [paper-dir | arxiv-id | pdf-path]
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, mcp__codex__codex
---

# Evidence Ledger — the foundation every auditor reads

> Infrastructure skill. It produces the **only** structure the auditor skills are
> allowed to reason over, so they don't each re-read the PDF and hallucinate a
> different structure. See `references/integrity-forensics-contract.md`.

Build the ledger for: **$ARGUMENTS**

## Why this exists

Five language-model auditors each independently parsing a PDF = five different
hallucinated tables and five different number lists. Instead, **one deterministic
pass** turns the paper into `claims.json` (`schemas/claims.schema.json`): a list of
span-anchored, hashed, checkable claims. Every downstream finding must cite a
`claim_id` from here — no ledger claim, no finding.

## Step 1 — Artifact manifest + observability level (deterministic)

Inventory what is actually available and derive the level (`references/
observability-levels.md`):

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# detect inputs in the target dir
ls *.tex *.pdf 2>/dev/null            # PDF / LaTeX source?
ls -d code/ src/ repo/ 2>/dev/null     # a repo present?
ls results/ outputs/ logs/ 2>/dev/null # result files present?
```

Write `artifact_manifest.json` (`schemas/artifact_manifest.schema.json`) recording
each artifact (kind, path, sha256, present) and the derived level:

```
repo + results present      -> L2
latex present, no results    -> L1
pdf only                     -> L0
```

**Never** claim a higher level than the artifacts support. The level caps every
downstream finding's severity.

## Step 2 — Extract the ledger (deterministic)

```bash
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# LaTeX-first (stable spans + line numbers):
python3 "$ROOT/tools/build_claim_ledger.py" --paper-id <id> \
    --latex main.tex sections/*.tex --observability-level <L> --out claims.json

# PDF-only: extract text first (pdftotext / mutool / pymupdf, whatever is present),
# then feed the text path at lower confidence:
#   pdftotext -layout paper.pdf paper.txt
python3 "$ROOT/tools/build_claim_ledger.py" --paper-id <id> \
    --pdf-text paper.txt --observability-level 0 --out claims.json
```

The extractor tags PDF-text numbers `confidence: low` — the human and adjudicator
weight them accordingly.

## Step 3 — LLM enrichment (additive, span-anchored, optional)

The regex extractor has high recall on *numeric/citation* surface but misses
*semantic* claims an auditor needs: the **method-description span**, **theorem
statements + their assumptions**, **explicit scope sentences**, **baseline lists**.
Use a single cross-model call (`mcp__codex__codex`, read-only, `cwd` = paper dir)
to ADD such claims to the ledger. Strict rules:

- It may only **add** claims, each with a verbatim `text_span` + `location` that
  exists in a source file (the executor verifies the span is a real substring).
- It may **never** invent a number or alter an extracted value.
- Tag enrichment claims `extractor: manual`, `confidence: medium`.

Prompt the reviewer for: `{type, text_span, location, (value if number)}` objects
only. Merge, re-id (`C001…`), and rewrite `claims.json`.

## Output

- `artifact_manifest.json` — what was observable (drives the level).
- `claims.json` — the evidence ledger (conforms to `schemas/claims.schema.json`).

## Key rules

- **Deterministic first.** The numeric/citation backbone comes from code, not a
  model — that is what makes the whole pipeline reproducible and defensible.
- **Spans are real.** Every `text_span` must be a verbatim substring of a hashed
  source file. The executor rejects any enrichment span it cannot locate.
- **No judgment here.** The ledger states *what the paper says*, never *whether it
  is right*. Judgment happens in the audit skills + the deterministic adjudicator.
